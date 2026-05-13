"""
System routes for metadata and API documentation.
Provides OpenAPI-style schema for frontend integration.
"""

from flask import Blueprint, jsonify

from config import FLASK_PORT, APP_ENV, now_iso
from models.database import db_manager
from models.ml_model import ml_manager
from services.bootstrap_service import seed_demo_showcase_data
from routes.decorators import api_key_required


system_bp = Blueprint('system', __name__)


@system_bp.route('/health', methods=['GET'])
def health_check():
    """Liveness probe endpoint."""
    return jsonify({'status': 'ok', 'env': APP_ENV}), 200


@system_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness probe endpoint with dependency checks."""
    db_ok = True
    db_error = None
    try:
        db_manager.execute_query("SELECT 1", fetch_one=True)
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    runtime_state = ml_manager.get_runtime_state()
    ml_ok = runtime_state['ready']

    ready = db_ok and ml_ok
    if db_ok and runtime_state['trained_model_loaded']:
        status = 'ready'
    elif db_ok and ml_ok:
        status = 'degraded'
    else:
        status = 'unavailable'

    status_code = 200 if ready else 503
    payload = {
        'status': status,
        'checks': {
            'database': {'ok': db_ok, 'error': db_error},
            'model': {
                'ok': ml_ok,
                'trained_model_loaded': runtime_state['trained_model_loaded'],
                'fallback_active': runtime_state['fallback_active'],
                'mode': runtime_state['mode'],
                'fallback_reason': runtime_state['fallback_reason'],
            },
        },
    }
    return jsonify(payload), status_code


@system_bp.route('/openapi.json', methods=['GET'])
def openapi_spec():
    """Serve a lightweight OpenAPI 3.0 spec for frontend/API tooling."""
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Motor Failure Prediction API',
            'version': '1.0.0',
            'description': 'Backend API for motor monitoring, OTP auth, predictions, alerts, and insights.'
        },
        'servers': [
            {'url': f'http://localhost:{FLASK_PORT}', 'description': 'Local development server'}
        ],
        'components': {
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT'
                },
                'ApiKeyAuth': {
                    'type': 'apiKey',
                    'in': 'header',
                    'name': 'X-API-Key'
                }
            }
        },
        'paths': {
            '/health': {'get': {'summary': 'Health check'}},
            '/ready': {'get': {'summary': 'Readiness check'}},
            '/openapi.json': {'get': {'summary': 'OpenAPI specification'}},

            '/auth/register': {'post': {'summary': 'Register user'}},
            '/auth/login': {'post': {'summary': 'Login and send OTP'}},
            '/auth/resend-otp': {'post': {'summary': 'Resend OTP'}},
            '/auth/verify-otp': {'post': {'summary': 'Verify OTP and issue bearer token'}},
            '/auth/logout': {
                'post': {
                    'summary': 'Logout current bearer session',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/auth/me': {
                'get': {
                    'summary': 'Current auth identity',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },

            '/motors': {
                'get': {
                    'summary': 'List active motors',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                },
                'post': {
                    'summary': 'Create motor',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/motors/{motor_id}': {
                'delete': {
                    'summary': 'Deactivate or hard-delete motor',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/motors/{motor_id}/reactivate': {
                'post': {
                    'summary': 'Reactivate motor',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/motors/readings/latest': {
                'get': {
                    'summary': 'Latest readings across motors',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/motors/{motor_id}/readings': {
                'get': {
                    'summary': 'Motor historical readings',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },

            '/predict/{motor_id}': {
                'get': {
                    'summary': 'Predict one motor',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/predict/batch': {
                'post': {
                    'summary': 'Batch prediction',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/predict/all': {
                'post': {
                    'summary': 'Predict all motors',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/explain/status/{motor_id}': {
                'get': {
                    'summary': 'SHAP status explanation',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/explain/rul/{motor_id}': {
                'get': {
                    'summary': 'SHAP RUL explanation',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },

            '/alerts': {
                'get': {
                    'summary': 'List alerts',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/alerts/{alert_id}/ack': {
                'post': {
                    'summary': 'Acknowledge one alert',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/alerts/batch/ack': {
                'post': {
                    'summary': 'Acknowledge multiple alerts',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },

            '/insights/status-distribution': {
                'get': {
                    'summary': 'Status distribution',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/insights/alerts-trend': {
                'get': {
                    'summary': 'Alerts trend',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/insights/sensor-trend/{motor_id}': {
                'get': {
                    'summary': 'Sensor trend for motor',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/insights/fleet-overview': {
                'get': {
                    'summary': 'Fleet KPI overview',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            },
            '/insights/live/stream': {
                'get': {
                    'summary': 'Live SSE stream for dashboard snapshots',
                    'description': 'Server-Sent Events endpoint. Use EventSource in frontend.',
                    'security': [{'BearerAuth': []}, {'ApiKeyAuth': []}]
                }
            }
        }
    }
    return jsonify(spec)


@system_bp.route('/dev/seed-demo-data', methods=['POST'])
@api_key_required
def seed_demo_data():
    """Seed demo motors/readings/alerts for development previews."""
    if APP_ENV == 'production':
        return jsonify({'error': 'Not available in production'}), 403

    try:
        summary = seed_demo_showcase_data()

        return jsonify(
            {
                'message': 'Demo data seeded successfully',
                'users_inserted': summary['users_inserted'],
                'motors_upserted': summary['motors_updated'],
                'sensor_readings_inserted': summary['sensor_readings_inserted'],
                'alerts_inserted': summary['alerts_inserted'],
                'timestamp': now_iso(),
            }
        )
    except Exception as exc:
        return jsonify({'error': f'Failed to seed demo data: {exc}'}), 500
