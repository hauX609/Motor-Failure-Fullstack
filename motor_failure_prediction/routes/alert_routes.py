"""
Alert routes for Motor Monitoring System.
Handles alert retrieval and acknowledgment.
"""

from flask import Blueprint, request, jsonify
import logging

from config import now_iso
from services.alert_service import alert_service
from utils.errors import ValidationError, NotFoundError, DatabaseError
from routes.decorators import api_key_required


logger = logging.getLogger(__name__)

alert_bp = Blueprint('alerts', __name__, url_prefix='/alerts')


@alert_bp.route('', methods=['GET'])
@api_key_required
def get_alerts():
    """Get alerts with optional filtering."""
    try:
        motor_id = request.args.get('motor_id')
        severity = request.args.get('severity')
        # Default to "all" so dashboard and alerts page return full history unless explicitly filtered.
        acknowledged_param = request.args.get('acknowledged', 'all').lower()
        limit = request.args.get('limit', 100, type=int)
        
        # Parse acknowledged parameter
        acknowledged = None
        if acknowledged_param == 'true':
            acknowledged = True
        elif acknowledged_param == 'false':
            acknowledged = False
        
        alerts = alert_service.get_alerts(motor_id, severity, acknowledged, limit)
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({'error': 'Failed to fetch alerts'}), 500


@alert_bp.route('/<int:alert_id>/ack', methods=['POST'])
@api_key_required
def acknowledge_alert(alert_id):
    """Acknowledge a specific alert."""
    try:
        alert_service.acknowledge_alert(alert_id)
        
        return jsonify({
            'message': f'Alert {alert_id} acknowledged',
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except NotFoundError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return jsonify({'error': 'Failed to acknowledge alert'}), 500


@alert_bp.route('/batch/ack', methods=['POST'])
@api_key_required
def batch_acknowledge_alerts():
    """Batch acknowledge multiple alerts."""
    try:
        data = request.get_json() or {}
        alert_ids = data.get('alert_ids', [])
        
        count = alert_service.batch_acknowledge_alerts(alert_ids)
        
        return jsonify({
            'message': f'{count} alerts acknowledged',
            'acknowledged_count': count,
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error batch acknowledging alerts: {e}")
        return jsonify({'error': 'Failed to batch acknowledge alerts'}), 500
