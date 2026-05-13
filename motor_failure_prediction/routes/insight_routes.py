"""
Insight routes for Motor Monitoring System.
Handles analytics and dashboard data.
"""

from flask import Blueprint, request, jsonify, Response
import logging
import json
import time

from config import now_iso
from services.insight_service import insight_service
from utils.errors import ValidationError, NotFoundError, DatabaseError
from routes.decorators import api_key_required


logger = logging.getLogger(__name__)

insight_bp = Blueprint('insights', __name__, url_prefix='/insights')


@insight_bp.route('/status-distribution', methods=['GET'])
@api_key_required
def status_distribution():
    """Get motor status distribution."""
    try:
        distribution = insight_service.get_status_distribution()
        
        return jsonify({
            'distribution': distribution,
            'timestamp': now_iso()
        })
    
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error getting status distribution: {e}")
        return jsonify({'error': 'Failed to get status distribution'}), 500


@insight_bp.route('/alerts-trend', methods=['GET'])
@api_key_required
def alerts_trend():
    """Get daily alerts trend by severity."""
    try:
        days = request.args.get('days', default=7, type=int)
        
        trend = insight_service.get_alerts_trend(days)
        
        return jsonify({
            'days': days,
            'trend': trend,
            'timestamp': now_iso()
        })
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error getting alerts trend: {e}")
        return jsonify({'error': 'Failed to get alerts trend'}), 500


@insight_bp.route('/sensor-trend/<string:motor_id>', methods=['GET'])
@api_key_required
def sensor_trend(motor_id):
    """Get sensor time series and statistics."""
    try:
        sensor = request.args.get('sensor', default='s11', type=str)
        limit = request.args.get('limit', default=200, type=int)
        
        trend_data = insight_service.get_sensor_trend(motor_id, sensor, limit)
        
        return jsonify(trend_data)
    
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except NotFoundError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error getting sensor trend: {e}")
        return jsonify({'error': 'Failed to get sensor trend'}), 500


@insight_bp.route('/fleet-overview', methods=['GET'])
@api_key_required
def fleet_overview():
    """Get fleet KPI counters."""
    try:
        overview = insight_service.get_fleet_overview()
        overview['timestamp'] = now_iso()
        
        return jsonify(overview)
    
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Error getting fleet overview: {e}")
        return jsonify({'error': 'Failed to get fleet overview'}), 500


@insight_bp.route('/live/stream', methods=['GET'])
@api_key_required
def live_stream():
    """Stream live fleet snapshots using Server-Sent Events (SSE)."""
    try:
        interval = request.args.get('interval', default=5, type=int)
        interval = max(2, min(interval, 60))

        def generate():
            while True:
                try:
                    payload = {
                        'timestamp': now_iso(),
                        'fleet_overview': insight_service.get_fleet_overview(),
                        'status_distribution': insight_service.get_status_distribution(),
                        'alerts_trend_24h': insight_service.get_alerts_trend(1),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                except Exception as stream_error:
                    logger.warning(f"Live stream frame generation failed: {stream_error}")
                    error_payload = {
                        'timestamp': now_iso(),
                        'error': 'Failed to fetch one live snapshot'
                    }
                    yield f"data: {json.dumps(error_payload)}\n\n"
                time.sleep(interval)

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        logger.error(f"Error starting live stream: {e}")
        return jsonify({'error': 'Failed to start live stream'}), 500
