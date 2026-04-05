"""
System routes for metadata and API documentation.
Provides OpenAPI-style schema for frontend integration.
"""

from flask import Blueprint, jsonify
from datetime import datetime, timedelta

from config import FLASK_PORT, APP_ENV, now_iso
from models.database import db_manager
from models.ml_model import ml_manager
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

    ml_ok = ml_manager.is_ready()

    ready = db_ok and ml_ok
    status_code = 200 if ready else 503
    payload = {
        'status': 'ready' if ready else 'degraded',
        'checks': {
            'database': {'ok': db_ok, 'error': db_error},
            'model': {'ok': ml_ok},
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

    seeded_motors = [
        ('Motor-DEV-HEALTHY-01', 'AC Induction', 'Optimal'),
        ('Motor-DEV-DEGRADING-01', 'Servo Motor', 'Degrading'),
        ('Motor-DEV-CRITICAL-01', 'DC Brushless', 'Critical'),
        ('Motor-DEV-DEGRADING-02', 'Stepper Motor', 'Degrading'),
        ('Motor-DEV-CRITICAL-02', 'AC Induction', 'Critical'),
    ]

    try:
        readings_inserted = 0
        alerts_inserted = 0

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            for motor_id, motor_type, status in seeded_motors:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO motors (motor_id, motor_type, installation_date, latest_status, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (motor_id, motor_type, now_iso(), status),
                )

                cursor.execute(
                    """
                    UPDATE motors
                    SET latest_status = ?, active = 1
                    WHERE motor_id = ?
                    """,
                    (status, motor_id),
                )

                base_s11 = 1.0
                if status == 'Degrading':
                    base_s11 = 1.6
                elif status == 'Critical':
                    base_s11 = 2.2

                now = datetime.utcnow()
                for idx in range(18):
                    ts = (now - timedelta(minutes=(18 - idx) * 5)).isoformat()
                    jitter = (idx % 5) * 0.02
                    cursor.execute(
                        """
                        INSERT INTO sensor_readings (motor_id, timestamp, setting1, setting2, setting3, s11)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            motor_id,
                            ts,
                            0.0,
                            0.0,
                            100.0,
                            base_s11 + jitter,
                        ),
                    )
                    readings_inserted += 1

                if status == 'Degrading':
                    cursor.execute(
                        """
                        INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                        VALUES (?, ?, ?, ?, 0)
                        """,
                        (
                            motor_id,
                            now_iso(),
                            'Degrading',
                            'Temperature drift detected. Monitor motor closely.',
                        ),
                    )
                    alerts_inserted += 1

                if status == 'Critical':
                    cursor.execute(
                        """
                        INSERT INTO alerts (motor_id, timestamp, severity, message, acknowledged)
                        VALUES (?, ?, ?, ?, 0)
                        """,
                        (
                            motor_id,
                            now_iso(),
                            'Critical',
                            'Critical vibration spike detected. Immediate inspection required.',
                        ),
                    )
                    alerts_inserted += 1

            conn.commit()

        return jsonify(
            {
                'message': 'Demo data seeded successfully',
                'motors_upserted': len(seeded_motors),
                'sensor_readings_inserted': readings_inserted,
                'alerts_inserted': alerts_inserted,
                'timestamp': now_iso(),
            }
        )
    except Exception as exc:
        return jsonify({'error': f'Failed to seed demo data: {exc}'}), 500
