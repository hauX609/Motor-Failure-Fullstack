"""
Prediction service for Motor Monitoring System.
Handles model predictions and inference.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from config import REQUIRED_SEQUENCE_LENGTH, STATUS_MAP
from models.database import db_manager
from models.ml_model import ml_manager
from utils.validators import Validator
from utils.errors import (
    ValidationError, ServiceUnavailableError,
    DatabaseError, NotFoundError
)


logger = logging.getLogger(__name__)


FALLBACK_BASELINES = {
    'setting1': 0.45,
    'setting2': 0.60,
    'setting3': 0.50,
    's4': 0.25,
    's7': 0.15,
    's11': 0.20,
    's13': 0.55,
    's14': 0.70,
}


class PredictionService:
    """Handles motor predictions."""

    @staticmethod
    def _fallback_prediction(sequence_df: pd.DataFrame, previous_status: str = None) -> Dict:
        """Generate a heuristic prediction when trained ML assets are unavailable."""
        if sequence_df.isnull().any().any():
            sequence_df = sequence_df.fillna(sequence_df.mean())

        key_columns = [col for col in ['s4', 's7', 's11', 's13', 's14'] if col in sequence_df.columns]
        if not key_columns:
            key_columns = list(sequence_df.select_dtypes(include=[np.number]).columns)

        if not key_columns:
            raise ValueError("No numeric sensor columns available for fallback prediction")

        latest_row = sequence_df[key_columns].iloc[-1].astype(float)
        history = sequence_df[key_columns].astype(float)

        severity_score = 0.0
        for column in key_columns:
            baseline = FALLBACK_BASELINES.get(column, float(history[column].median()))
            current_value = float(latest_row[column])
            deviation = max(0.0, current_value - baseline)
            weight = {
                's11': 34.0,
                's14': 26.0,
                's4': 18.0,
                's7': 12.0,
                's13': 10.0,
            }.get(column, 8.0)
            severity_score += deviation * weight * 100.0

        if 's11' in history.columns and len(history) > 1:
            severity_score += max(0.0, float(history['s11'].iloc[-1] - history['s11'].iloc[0])) * 120.0

        severity_score = float(np.clip(severity_score, 0.0, 100.0))

        if severity_score < 25.0:
            predicted_status = 'Optimal'
            probabilities = [0.84, 0.11, 0.05]
        elif severity_score < 55.0:
            predicted_status = 'Degrading'
            probabilities = [0.18, 0.64, 0.18]
        else:
            predicted_status = 'Critical'
            probabilities = [0.06, 0.16, 0.78]

        predicted_rul = max(0.0, round(500.0 - severity_score * 4.5, 2))

        alert_needed = False
        if previous_status and predicted_status != 'Optimal':
            status_priority = {'Optimal': 0, 'Degrading': 1, 'Critical': 2}
            if status_priority.get(predicted_status, -1) > status_priority.get(previous_status, -1):
                alert_needed = True

        return {
            'motor_id': None,
            'predicted_status': predicted_status,
            'predicted_rul': predicted_rul,
            'probabilities': probabilities,
            'previous_status': previous_status,
            'alert_needed': alert_needed,
            'success': True,
            'prediction_mode': 'fallback',
            'risk_level': 'high' if predicted_status == 'Critical' else 'medium' if predicted_status == 'Degrading' else 'low',
        }
    
    @staticmethod
    def get_latest_sequence_from_db(motor_id: str) -> pd.DataFrame:
        """Get latest sensor sequence for a motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            if not ml_manager.is_ready():
                raise ServiceUnavailableError("Model not ready")
            
            feature_cols_str = ', '.join(f'"{col}"' for col in ml_manager.feature_cols)
            query = f"""
                SELECT {feature_cols_str} 
                FROM sensor_readings 
                WHERE motor_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            
            df = db_manager.execute_pandas_query(
                query,
                (motor_id, REQUIRED_SEQUENCE_LENGTH)
            )
            
            if df.empty:
                raise NotFoundError(f"No data found for motor {motor_id}")
            
            # Reverse to get chronological order
            return df.reindex(index=df.index[::-1]).reset_index(drop=True)
        
        except (ValidationError, ServiceUnavailableError, NotFoundError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting sequence for {motor_id}: {e}")
            raise DatabaseError(f"Failed to get sequence: {str(e)}")
    
    @staticmethod
    def get_multiple_sequences_from_db(motor_ids: List[str]) -> Dict[str, pd.DataFrame]:
        """Get sequences for multiple motors."""
        if not motor_ids or not all(Validator.validate_motor_id(mid) for mid in motor_ids):
            raise ValidationError("Invalid motor IDs")
        
        try:
            if not ml_manager.is_ready():
                raise ServiceUnavailableError("Model not ready")
            
            placeholders = ','.join(['?' for _ in motor_ids])
            feature_cols_str = ', '.join(f'"{col}"' for col in ml_manager.feature_cols)
            
            query = f"""
            WITH ranked_readings AS (
                SELECT motor_id, {feature_cols_str}, timestamp,
                       ROW_NUMBER() OVER (PARTITION BY motor_id ORDER BY timestamp DESC) as rn
                FROM sensor_readings
                WHERE motor_id IN ({placeholders})
            )
            SELECT motor_id, {feature_cols_str}
            FROM ranked_readings
            WHERE rn <= ?
            ORDER BY motor_id, timestamp ASC
            """
            
            df = db_manager.execute_pandas_query(
                query,
                tuple(motor_ids) + (REQUIRED_SEQUENCE_LENGTH,)
            )
            
            # Group by motor_id
            motor_sequences = {}
            for motor_id, group in df.groupby('motor_id'):
                motor_sequences[motor_id] = group[ml_manager.feature_cols].reset_index(drop=True)
            
            return motor_sequences
        
        except (ValidationError, ServiceUnavailableError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error getting multiple sequences: {e}")
            raise DatabaseError(f"Failed to get multiple sequences: {str(e)}")
    
    @staticmethod
    def predict_single_motor(motor_id: str, sequence_df: pd.DataFrame,
                            previous_status: str = None) -> Dict:
        """Predict status and RUL for a single motor."""
        try:
            if not Validator.validate_motor_id(motor_id):
                raise ValidationError("Invalid motor ID")
            
            if not ml_manager.is_ready():
                raise ServiceUnavailableError("Model not ready")
            
            if len(sequence_df) < REQUIRED_SEQUENCE_LENGTH:
                raise NotFoundError(
                    f"Not enough data. Need {REQUIRED_SEQUENCE_LENGTH}, got {len(sequence_df)}"
                )

            if ml_manager.fallback_mode:
                result = PredictionService._fallback_prediction(sequence_df, previous_status)
                result['motor_id'] = motor_id
                return result
            
            # Handle null values
            if sequence_df.isnull().any().any():
                logger.warning(f"Motor {motor_id} has null values, filling with column means")
                sequence_df = sequence_df.fillna(sequence_df.mean())
            
            # Make prediction
            with ml_manager.model_lock:
                scaled_sequence = ml_manager.feature_scaler.transform(sequence_df)
                reshaped_sequence = np.expand_dims(scaled_sequence, axis=0)
                predictions = ml_manager.model.predict(reshaped_sequence, verbose=0)
                
                if len(predictions) != 2:
                    raise ValueError("Model should return 2 outputs")
            
            class_prediction, reg_prediction = predictions
            predicted_class_index = np.argmax(class_prediction, axis=1)[0]
            predicted_status = STATUS_MAP.get(predicted_class_index, "Unknown")
            
            # Get RUL prediction
            scaled_rul = reg_prediction[0]
            predicted_rul = ml_manager.rul_scaler.inverse_transform([scaled_rul])[0][0]
            predicted_rul = max(0, float(predicted_rul))
            
            # Check if alert needed
            alert_needed = False
            if previous_status and predicted_status != 'Optimal':
                status_priority = {'Optimal': 0, 'Degrading': 1, 'Critical': 2}
                if (status_priority.get(predicted_status, -1) > 
                    status_priority.get(previous_status, -1)):
                    alert_needed = True
            
            return {
                'motor_id': motor_id,
                'predicted_status': predicted_status,
                'predicted_rul': round(predicted_rul, 2),
                'probabilities': [float(p) for p in class_prediction[0]],
                'previous_status': previous_status,
                'alert_needed': alert_needed,
                'success': True
            }
        
        except (ValidationError, ServiceUnavailableError, NotFoundError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Prediction error for {motor_id}: {e}")
            return {
                'motor_id': motor_id,
                'error': f'Prediction failed: {str(e)}',
                'success': False
            }


# Global prediction service instance
prediction_service = PredictionService()
