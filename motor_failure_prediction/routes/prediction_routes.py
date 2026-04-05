"""
Prediction routes for Motor Monitoring System.
Handles single, batch, and all-motor predictions.
"""

from flask import Blueprint, request, jsonify
import logging
import time
import numpy as np

from config import now_iso, MAX_BATCH_SIZE, REQUIRED_SEQUENCE_LENGTH
from services.prediction_service import prediction_service
from services.motor_service import motor_service
from services.alert_service import alert_service
from models.ml_model import ml_manager
from utils.validators import Validator
from utils.errors import (
    ValidationError, ServiceUnavailableError, NotFoundError,
    DatabaseError
)
from routes.decorators import api_key_required


logger = logging.getLogger(__name__)

prediction_bp = Blueprint('predictions', __name__)


@prediction_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        try:
            from models.database import db_manager
            db_manager.execute_query("SELECT 1", fetch_one=True)
            db_healthy = True
        except Exception:
            db_healthy = False
        
        return jsonify({
            'status': 'healthy' if (ml_manager.is_ready() and db_healthy) else 'unhealthy',
            'timestamp': now_iso(),
            'model_loaded': ml_manager.is_ready(),
            'explainers_loaded': ml_manager.has_explainers(),
            'database_accessible': db_healthy,
            'feature_count': ml_manager.get_feature_count()
        })
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


@prediction_bp.route('/predict/<string:motor_id>', methods=['GET'])
@api_key_required
def predict(motor_id):
    """Predict motor status and RUL."""
    try:
        if not Validator.validate_motor_id(motor_id):
            return jsonify({'error': 'Invalid motor ID format'}), 400
        
        if not ml_manager.is_ready():
            return jsonify({'error': 'Model not loaded'}), 503
        
        # Get sequence
        sequence_df = prediction_service.get_latest_sequence_from_db(motor_id)
        previous_status = motor_service.get_motor_status(motor_id)
        
        # Make prediction
        result = prediction_service.predict_single_motor(motor_id, sequence_df, previous_status)
        
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Prediction failed')}), 404
        
        # Create alert if needed
        if result['alert_needed'] and result['predicted_status'] != 'Optimal':
            message = (
                f"Status changed from {result['previous_status']} to {result['predicted_status']}. "
                f"Predicted RUL: {result['predicted_rul']:.0f}"
            )
            try:
                alert_service.create_alert(motor_id, result['predicted_status'], message)
            except Exception as e:
                logger.warning(f"Failed to create alert: {e}")
        
        # Update motor status
        motor_service.update_motor_status(motor_id, result['predicted_status'])
        
        return jsonify({
            'motor_id': result['motor_id'],
            'predicted_status': result['predicted_status'],
            'predicted_rul': result['predicted_rul'],
            'probabilities': result['probabilities'],
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except (ServiceUnavailableError, NotFoundError) as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': 'Prediction failed'}), 500


@prediction_bp.route('/predict/batch', methods=['POST'])
@api_key_required
def batch_predict():
    """Batch predict for multiple motors."""
    start_time = time.time()
    try:
        data = request.get_json() or {}
        motor_ids = data.get('motor_ids', [])
        max_motors = data.get('max_motors', MAX_BATCH_SIZE)
        
        if not isinstance(motor_ids, list) or len(motor_ids) == 0:
            return jsonify({'error': 'motor_ids must be a non-empty array'}), 400
        
        if len(motor_ids) > max_motors:
            return jsonify({'error': f'Too many motors. Maximum: {max_motors}'}), 400
        
        if not all(Validator.validate_motor_id(mid) for mid in motor_ids):
            return jsonify({'error': 'One or more invalid motor IDs'}), 400
        
        if not ml_manager.is_ready():
            return jsonify({'error': 'Model not loaded'}), 503
        
        # Get sequences
        motor_sequences = prediction_service.get_multiple_sequences_from_db(motor_ids)
        previous_statuses = motor_service.get_multiple_motor_statuses(motor_ids)
        
        # Filter valid motors
        valid_motors = {mid: seq for mid, seq in motor_sequences.items() 
                       if len(seq) >= REQUIRED_SEQUENCE_LENGTH}
        invalid_motors = [mid for mid in motor_ids if mid not in valid_motors]
        
        if not valid_motors:
            return jsonify({
                'error': 'No motors have sufficient data',
                'invalid_motors': invalid_motors
            }), 404
        
        # Prepare batch prediction
        motor_list = list(valid_motors.keys())
        processed_sequences = []
        
        for motor_id in motor_list:
            seq_df = valid_motors[motor_id]
            if seq_df.isnull().any().any():
                logger.warning(f"Motor {motor_id} has null values, filling")
                seq_df = seq_df.fillna(seq_df.mean())
            processed_sequences.append(ml_manager.feature_scaler.transform(seq_df))
        
        sequences_array = np.array(processed_sequences)
        
        # Batch prediction
        with ml_manager.model_lock:
            predictions = ml_manager.model.predict(sequences_array, verbose=0)
            if len(predictions) != 2:
                raise ValueError("Model should return 2 outputs")
        
        class_predictions, reg_predictions = predictions
        
        # Process results
        results = []
        alerts_to_create = []
        status_updates = []
        
        for i, motor_id in enumerate(motor_list):
            try:
                predicted_class_index = np.argmax(class_predictions[i])
                from config import STATUS_MAP
                predicted_status = STATUS_MAP.get(predicted_class_index, "Unknown")
                predicted_rul = max(0, float(
                    ml_manager.rul_scaler.inverse_transform([reg_predictions[i]])[0][0]
                ))
                previous_status = previous_statuses.get(motor_id, 'Optimal')
                
                # Check for alert
                status_priority = {'Optimal': 0, 'Degrading': 1, 'Critical': 2}
                if (predicted_status != 'Optimal' and 
                    status_priority.get(predicted_status, -1) > 
                    status_priority.get(previous_status, -1)):
                    alerts_to_create.append({
                        'motor_id': motor_id,
                        'severity': predicted_status,
                        'message': (
                            f"Status changed from {previous_status} to {predicted_status}. "
                            f"Predicted RUL: {predicted_rul:.0f}"
                        )
                    })
                
                status_updates.append((motor_id, predicted_status))
                
                results.append({
                    'motor_id': motor_id,
                    'predicted_status': predicted_status,
                    'predicted_rul': round(predicted_rul, 2),
                    'probabilities': [float(p) for p in class_predictions[i]],
                    'previous_status': previous_status
                })
            
            except Exception as e:
                logger.error(f"Error processing {motor_id}: {e}")
                results.append({
                    'motor_id': motor_id,
                    'error': f'Processing failed: {str(e)}',
                    'success': False
                })
        
        # Batch DB operations
        if status_updates:
            motor_service.batch_update_motor_statuses(status_updates)
        
        if alerts_to_create:
            alert_service.batch_create_alerts(alerts_to_create)
        
        failed_results = [
            {
                'motor_id': mid,
                'error': f'Not enough data. Need {REQUIRED_SEQUENCE_LENGTH}',
                'success': False
            }
            for mid in invalid_motors
        ]
        
        processing_time = round(time.time() - start_time, 3)
        
        return jsonify({
            'success': True,
            'total_requested': len(motor_ids),
            'successful_predictions': len([r for r in results if r.get('success', True)]),
            'failed_predictions': len(failed_results) + len([r for r in results if not r.get('success', True)]),
            'alerts_created': len(alerts_to_create),
            'processing_time_seconds': processing_time,
            'predictions': results,
            'failed_motors': failed_results,
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return jsonify({'error': 'Batch prediction failed'}), 500


@prediction_bp.route('/predict/all', methods=['POST'])
@api_key_required
def predict_all():
    """Predict for all active motors."""
    start_time = time.time()
    try:
        if not ml_manager.is_ready():
            return jsonify({'error': 'Model not loaded'}), 503
        
        motor_ids = motor_service.get_all_active_motors()
        
        if not motor_ids:
            return jsonify({'error': 'No motors found'}), 404
        
        logger.info(f"Predicting for {len(motor_ids)} motors")
        
        # Get sequences
        motor_sequences = prediction_service.get_multiple_sequences_from_db(motor_ids)
        previous_statuses = motor_service.get_multiple_motor_statuses(motor_ids)
        
        # Filter valid motors
        valid_motors = {mid: seq for mid, seq in motor_sequences.items() 
                       if len(seq) >= REQUIRED_SEQUENCE_LENGTH}
        invalid_motors = [mid for mid in motor_ids if mid not in valid_motors]
        
        if not valid_motors:
            return jsonify({
                'error': 'No motors have sufficient data',
                'total_motors': len(motor_ids),
                'invalid_motors': invalid_motors
            }), 404
        
        # Batch prediction
        motor_list = list(valid_motors.keys())
        processed_sequences = []
        
        for motor_id in motor_list:
            seq_df = valid_motors[motor_id]
            if seq_df.isnull().any().any():
                seq_df = seq_df.fillna(seq_df.mean())
            processed_sequences.append(ml_manager.feature_scaler.transform(seq_df))
        
        sequences_array = np.array(processed_sequences)
        
        with ml_manager.model_lock:
            predictions = ml_manager.model.predict(sequences_array, verbose=0)
            if len(predictions) != 2:
                raise ValueError("Model should return 2 outputs")
        
        class_predictions, reg_predictions = predictions
        
        results = []
        alerts_to_create = []
        status_updates = []
        
        for i, motor_id in enumerate(motor_list):
            try:
                predicted_class_index = np.argmax(class_predictions[i])
                from config import STATUS_MAP
                predicted_status = STATUS_MAP.get(predicted_class_index, "Unknown")
                predicted_rul = max(0, float(
                    ml_manager.rul_scaler.inverse_transform([reg_predictions[i]])[0][0]
                ))
                previous_status = previous_statuses.get(motor_id, 'Optimal')
                
                status_priority = {'Optimal': 0, 'Degrading': 1, 'Critical': 2}
                if (predicted_status != 'Optimal' and 
                    status_priority.get(predicted_status, -1) > 
                    status_priority.get(previous_status, -1)):
                    alerts_to_create.append({
                        'motor_id': motor_id,
                        'severity': predicted_status,
                        'message': (
                            f"Status changed from {previous_status} to {predicted_status}. "
                            f"Predicted RUL: {predicted_rul:.0f}"
                        )
                    })
                
                status_updates.append((motor_id, predicted_status))
                
                results.append({
                    'motor_id': motor_id,
                    'predicted_status': predicted_status,
                    'predicted_rul': round(predicted_rul, 2),
                    'probabilities': [float(p) for p in class_predictions[i]],
                    'previous_status': previous_status
                })
            
            except Exception as e:
                logger.error(f"Error processing {motor_id}: {e}")
                results.append({
                    'motor_id': motor_id,
                    'error': f'Processing failed: {str(e)}',
                    'success': False
                })
        
        # Batch DB operations
        if status_updates:
            motor_service.batch_update_motor_statuses(status_updates)
        
        if alerts_to_create:
            alert_service.batch_create_alerts(alerts_to_create)
        
        failed_results = [
            {
                'motor_id': mid,
                'error': f'Not enough data. Need {REQUIRED_SEQUENCE_LENGTH}',
                'success': False
            }
            for mid in invalid_motors
        ]
        
        processing_time = round(time.time() - start_time, 3)
        
        return jsonify({
            'success': True,
            'total_motors': len(motor_ids),
            'successful_predictions': len([r for r in results if r.get('success', True)]),
            'failed_predictions': len(failed_results) + len([r for r in results if not r.get('success', True)]),
            'alerts_created': len(alerts_to_create),
            'processing_time_seconds': processing_time,
            'predictions': results,
            'failed_motors': failed_results,
            'timestamp': now_iso()
        })
    
    except Exception as e:
        logger.error(f"Predict all error: {e}")
        return jsonify({'error': 'Predict all failed'}), 500


@prediction_bp.route('/explain/status/<string:motor_id>', methods=['GET'])
@api_key_required
def explain_status(motor_id):
    """Explain status prediction using SHAP."""
    try:
        if not ml_manager.has_explainers():
            return jsonify({'error': 'Explainers not available'}), 503
        
        if not Validator.validate_motor_id(motor_id):
            return jsonify({'error': 'Invalid motor ID'}), 400
        
        sequence_df = prediction_service.get_latest_sequence_from_db(motor_id)
        
        if len(sequence_df) < REQUIRED_SEQUENCE_LENGTH:
            return jsonify({
                'error': f'Not enough data. Need {REQUIRED_SEQUENCE_LENGTH}'
            }), 404
        
        # Handle null values
        if sequence_df.isnull().any().any():
            logger.warning(f"Motor {motor_id} has nulls, filling")
            sequence_df = sequence_df.fillna(sequence_df.mean())
        
        with ml_manager.model_lock:
            scaled_sequence = ml_manager.feature_scaler.transform(sequence_df)
            reshaped_sequence = np.expand_dims(scaled_sequence, axis=0)
            shap_values = ml_manager.classification_explainer.shap_values(reshaped_sequence)
        
        if isinstance(shap_values, list):
            shap_vals = shap_values[0] if len(shap_values) > 0 else shap_values
        else:
            shap_vals = shap_values
        
        mean_abs_shap = np.mean(np.abs(shap_vals), axis=(0, 1))
        if mean_abs_shap.ndim > 1:
            mean_abs_shap = mean_abs_shap.flatten()
        
        feature_importance_pairs = list(zip(ml_manager.feature_cols, mean_abs_shap))
        feature_importance = sorted(feature_importance_pairs, key=lambda x: float(x[1]), reverse=True)
        
        return jsonify({
            'motor_id': motor_id,
            'explanation_for': 'status',
            'feature_importance': {f: float(imp) for f, imp in feature_importance},
            'top_features': feature_importance[:10],
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Status explanation error: {e}")
        return jsonify({'error': 'Explanation failed'}), 500


@prediction_bp.route('/explain/rul/<string:motor_id>', methods=['GET'])
@api_key_required
def explain_rul(motor_id):
    """Explain RUL prediction using SHAP."""
    try:
        if not ml_manager.has_explainers():
            return jsonify({'error': 'Explainers not available'}), 503
        
        if not Validator.validate_motor_id(motor_id):
            return jsonify({'error': 'Invalid motor ID'}), 400
        
        sequence_df = prediction_service.get_latest_sequence_from_db(motor_id)
        
        if len(sequence_df) < REQUIRED_SEQUENCE_LENGTH:
            return jsonify({
                'error': f'Not enough data. Need {REQUIRED_SEQUENCE_LENGTH}'
            }), 404
        
        if sequence_df.isnull().any().any():
            logger.warning(f"Motor {motor_id} has nulls, filling")
            sequence_df = sequence_df.fillna(sequence_df.mean())
        
        with ml_manager.model_lock:
            scaled_sequence = ml_manager.feature_scaler.transform(sequence_df)
            reshaped_sequence = np.expand_dims(scaled_sequence, axis=0)
            shap_values = ml_manager.regression_explainer.shap_values(reshaped_sequence)
        
        if isinstance(shap_values, list):
            shap_vals = shap_values[0] if len(shap_values) > 0 else shap_values
        else:
            shap_vals = shap_values
        
        mean_abs_shap = np.mean(np.abs(shap_vals), axis=(0, 1))
        if mean_abs_shap.ndim > 1:
            mean_abs_shap = mean_abs_shap.flatten()
        
        feature_importance_pairs = list(zip(ml_manager.feature_cols, mean_abs_shap))
        feature_importance = sorted(feature_importance_pairs, key=lambda x: float(x[1]), reverse=True)
        
        return jsonify({
            'motor_id': motor_id,
            'explanation_for': 'rul',
            'feature_importance': {f: float(imp) for f, imp in feature_importance},
            'top_features': feature_importance[:10],
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"RUL explanation error: {e}")
        return jsonify({'error': 'Explanation failed'}), 500
