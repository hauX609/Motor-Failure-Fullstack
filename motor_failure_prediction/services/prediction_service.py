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


class PredictionService:
    """Handles motor predictions."""
    
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
