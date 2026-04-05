"""
Motor Failure Prediction System - Main Application
A modular Flask application for predictive maintenance.
"""

import warnings
import time
import uuid
from flask import Flask, jsonify, g, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from config import (
    setup_logging,
    FLASK_HOST,
    FLASK_PORT,
    FLASK_THREADED,
    FLASK_USE_RELOADER,
    CORS_ALLOWED_ORIGINS,
    APP_ENV,
    SECRET_API_KEY,
    MAX_CONTENT_LENGTH,
    TRUST_PROXY_HEADERS,
    PROXY_FIX_X_FOR,
    PROXY_FIX_X_PROTO,
    PROXY_FIX_X_HOST,
    PROXY_FIX_X_PORT,
    PROXY_FIX_X_PREFIX,
    REQUEST_LOGGING_ENABLED,
    SECURITY_HEADERS_ENABLED,
)
from models.ml_model import ml_manager
from routes.auth_routes import auth_bp
from routes.motor_routes import motor_bp
from routes.alert_routes import alert_bp
from routes.insight_routes import insight_bp
from routes.prediction_routes import prediction_bp
from routes.system_routes import system_bp
from services.bootstrap_service import ensure_baseline_operational_data


# Suppress TensorFlow warnings
warnings.filterwarnings('ignore')

# Setup logging
logger = setup_logging()

def register_blueprints(app: Flask):
    """Register all route blueprints."""
    app.register_blueprint(system_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(motor_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(insight_bp)
    app.register_blueprint(prediction_bp)


def register_error_handlers(app: Flask):
    """Register global error handlers."""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found', 'request_id': getattr(g, 'request_id', '-') }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed', 'request_id': getattr(g, 'request_id', '-') }), 405

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error")
        return jsonify({'error': 'Internal server error', 'request_id': getattr(g, 'request_id', '-') }), 500

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        if isinstance(error, HTTPException):
            return error
        logger.exception("Unhandled exception")
        return jsonify({'error': 'Internal server error', 'request_id': getattr(g, 'request_id', '-') }), 500


def register_request_hooks(app: Flask):
    """Attach request tracing, access logging, and security headers."""

    @app.before_request
    def before_request():
        request_id = (request.headers.get('X-Request-ID') or '').strip()
        g.request_id = request_id or uuid.uuid4().hex[:16]
        g.request_start = time.perf_counter()

    @app.after_request
    def after_request(response):
        response.headers['X-Request-ID'] = getattr(g, 'request_id', '-')

        if SECURITY_HEADERS_ENABLED:
            response.headers.setdefault('X-Content-Type-Options', 'nosniff')
            response.headers.setdefault('X-Frame-Options', 'DENY')
            response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
            response.headers.setdefault('X-XSS-Protection', '0')
            if APP_ENV == 'production':
                response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

        if REQUEST_LOGGING_ENABLED:
            started = getattr(g, 'request_start', None)
            elapsed_ms = (time.perf_counter() - started) * 1000 if started else -1
            logger.info(
                "request method=%s path=%s status=%s duration_ms=%.2f ip=%s",
                request.method,
                request.path,
                response.status_code,
                elapsed_ms,
                request.headers.get('X-Forwarded-For', request.remote_addr),
            )

        return response


def validate_production_config():
    """Fail fast when required production configuration is missing."""
    if APP_ENV != 'production':
        return

    if not SECRET_API_KEY:
        logger.error("MOTOR_API_KEY is required when APP_ENV=production. Refusing to start.")
        raise RuntimeError("Missing required env var: MOTOR_API_KEY")

    if not CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGINS == '*':
        logger.error("CORS_ALLOWED_ORIGINS must be set to explicit origin(s) when APP_ENV=production.")
        raise RuntimeError("Missing/invalid env var: CORS_ALLOWED_ORIGINS")


def initialize_runtime():
    """Initialize heavy runtime dependencies once at startup."""
    logger.info("=" * 50)
    logger.info("Starting Motor Failure Prediction System")
    logger.info("=" * 50)

    logger.info("Loading ML model assets...")
    if not ml_manager.load_assets():
        logger.error("Failed to load model assets. Continuing without predictions...")
    else:
        logger.info("Initializing SHAP explainers...")
        ml_manager.initialize_explainers()

    logger.info("Ensuring baseline operational data...")
    ensure_baseline_operational_data()

    logger.info("Runtime initialization complete")


def create_app() -> Flask:
    """Application factory for WSGI servers and local execution."""
    validate_production_config()

    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    if TRUST_PROXY_HEADERS:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=PROXY_FIX_X_FOR,
            x_proto=PROXY_FIX_X_PROTO,
            x_host=PROXY_FIX_X_HOST,
            x_port=PROXY_FIX_X_PORT,
            x_prefix=PROXY_FIX_X_PREFIX,
        )

    CORS(
        app,
        resources={r"/*": {"origins": CORS_ALLOWED_ORIGINS}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    register_blueprints(app)
    register_error_handlers(app)
    register_request_hooks(app)

    initialize_runtime()
    return app


app = create_app()


def main():
    """Initialize and run the application."""
    logger.info("=" * 50)
    logger.info("Starting Flask development server on %s:%s", FLASK_HOST, FLASK_PORT)
    logger.info("=" * 50)

    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        use_reloader=FLASK_USE_RELOADER,
        threaded=FLASK_THREADED
    )


if __name__ == '__main__':
    main()
