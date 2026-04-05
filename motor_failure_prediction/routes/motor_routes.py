"""
Motor routes for Motor Monitoring System.
Handles motor CRUD and listing operations.
"""

from flask import Blueprint, request, jsonify
import logging

from config import now_iso
from services.motor_service import motor_service
from models.database import db_manager
from utils.errors import ValidationError, NotFoundError, ConflictError, DatabaseError
from routes.decorators import api_key_required


logger = logging.getLogger(__name__)

motor_bp = Blueprint('motors', __name__, url_prefix='/motors')


@motor_bp.route('', methods=['GET'])
@api_key_required
def get_motors():
    """Get list of all active motors."""
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        motors = motor_service.get_motors(include_inactive=include_inactive)

        if not motors:
            return jsonify({
                'motors': [],
                'count': 0,
                'timestamp': now_iso()
            })

        return jsonify({
            'motors': motors,
            'count': len(motors),
            'include_inactive': include_inactive,
            'timestamp': now_iso()
        })
    
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error fetching motors: {e}")
        return jsonify({'error': 'Failed to fetch motors'}), 500


@motor_bp.route('', methods=['POST'])
@api_key_required
def create_motor():
    """Create a new motor."""
    try:
        data = request.get_json() or {}
        motor_id = (data.get('motor_id') or '').strip()
        motor_type = (data.get('motor_type') or '').strip()
        installation_date = (data.get('installation_date') or '').strip()
        location = (data.get('location') or '').strip()
        
        motor_data = motor_service.create_motor(motor_id, motor_type, installation_date or None, location or None)
        
        return jsonify({
            'message': 'Motor created successfully',
            'motor': motor_data,
            'timestamp': now_iso()
        }), 201
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except ConflictError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error creating motor: {e}")
        return jsonify({'error': 'Failed to create motor'}), 500


@motor_bp.route('/<string:motor_id>', methods=['DELETE'])
@api_key_required
def delete_motor(motor_id):
    """Delete or deactivate a motor."""
    try:
        hard_delete = request.args.get('hard', 'false').lower() == 'true'
        
        action = motor_service.delete_motor(motor_id, hard_delete)
        
        return jsonify({
            'message': f'Motor {action} successfully',
            'motor_id': motor_id,
            'action': action,
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except NotFoundError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error deleting motor: {e}")
        return jsonify({'error': 'Failed to delete motor'}), 500


@motor_bp.route('/<string:motor_id>', methods=['GET'])
@api_key_required
def get_motor_details(motor_id):
    """Get details for a specific motor."""
    try:
        motor = db_manager.get_motor(motor_id)
        if not motor:
            return jsonify({'error': 'Motor not found'}), 404

        latest_status = motor.get('latest_status') or motor.get('status') or 'Optimal'

        return jsonify({
            'id': motor.get('motor_id'),
            'motor_id': motor.get('motor_id'),
            'name': motor.get('motor_id'),
            'motor_type': motor.get('motor_type'),
            'model': motor.get('motor_type'),
            'location': motor.get('location'),
            'status': latest_status,
            'latest_status': latest_status,
            'active': motor.get('active', 1),
            'installation_date': motor.get('installation_date'),
            'timestamp': now_iso(),
        })

    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error fetching motor details: {e}")
        return jsonify({'error': 'Failed to fetch motor details'}), 500


@motor_bp.route('/<string:motor_id>/reactivate', methods=['POST'])
@api_key_required
def reactivate_motor(motor_id):
    """Reactivate a deactivated motor."""
    try:
        motor_service.reactivate_motor(motor_id)
        
        return jsonify({
            'message': 'Motor reactivated successfully',
            'motor_id': motor_id,
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except NotFoundError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error reactivating motor: {e}")
        return jsonify({'error': 'Failed to reactivate motor'}), 500


@motor_bp.route('/readings/latest', methods=['GET'])
@api_key_required
def get_latest_readings_for_all():
    """Get latest sensor reading for all motors."""
    try:
        from services.insight_service import insight_service
        
        readings = insight_service.get_latest_readings()
        
        return jsonify({
            'latest_readings': readings,
            'count': len(readings),
            'timestamp': now_iso()
        })
    
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error fetching latest readings: {e}")
        return jsonify({'error': 'Failed to fetch latest readings'}), 500


@motor_bp.route('/<string:motor_id>/readings', methods=['GET'])
@api_key_required
def get_motor_readings_history(motor_id):
    """Get historical readings for a specific motor."""
    try:
        from services.insight_service import insight_service
        
        limit = request.args.get('limit', default=200, type=int)
        
        readings = insight_service.get_motor_readings_history(motor_id, limit)
        
        return jsonify({
            'motor_id': motor_id,
            'readings': readings,
            'count': len(readings),
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error fetching motor readings: {e}")
        return jsonify({'error': 'Failed to fetch motor readings'}), 500
