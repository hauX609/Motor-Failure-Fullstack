"""
Configuration module for Motor Monitoring System.
Centralizes all constants and environment variables.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from dotenv import load_dotenv
from flask import has_request_context, g


# Load environment variables from .env for local/dev runs.
load_dotenv()

# Database Configuration
DB_FILE = "motors.db"
DB_TIMEOUT = 30

# API Configuration
SECRET_API_KEY = (os.getenv('MOTOR_API_KEY') or '').strip()
MAX_BATCH_SIZE = 100

# ML Model Configuration
REQUIRED_SEQUENCE_LENGTH = 50
STATUS_MAP = {0: 'Optimal', 1: 'Degrading', 2: 'Critical'}

# Authentication Configuration
OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', '10'))
SESSION_EXPIRY_HOURS = int(os.getenv('SESSION_EXPIRY_HOURS', '12'))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv('OTP_RESEND_COOLDOWN_SECONDS', '60'))
OTP_MAX_REQUESTS_PER_HOUR = int(os.getenv('OTP_MAX_REQUESTS_PER_HOUR', '5'))
OTP_MAX_VERIFY_ATTEMPTS = int(os.getenv('OTP_MAX_VERIFY_ATTEMPTS', '5'))
OTP_VERIFY_LOCKOUT_MINUTES = int(os.getenv('OTP_VERIFY_LOCKOUT_MINUTES', '15'))

# Email Configuration
ALERT_EMAIL_ENABLED = os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_FROM = os.getenv('SMTP_FROM_EMAIL', SMTP_USER)
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
DEV_OTP_IN_RESPONSE = os.getenv('DEV_OTP_IN_RESPONSE', 'true').lower() == 'true'

# Flask Configuration
APP_ENV = os.getenv('APP_ENV', 'development').strip().lower()
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5001'))
FLASK_THREADED = True
FLASK_USE_RELOADER = False


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


MAX_CONTENT_LENGTH_MB = int(os.getenv('MAX_CONTENT_LENGTH_MB', '10'))
MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024
TRUST_PROXY_HEADERS = _env_bool('TRUST_PROXY_HEADERS', APP_ENV == 'production')
PROXY_FIX_X_FOR = int(os.getenv('PROXY_FIX_X_FOR', '1'))
PROXY_FIX_X_PROTO = int(os.getenv('PROXY_FIX_X_PROTO', '1'))
PROXY_FIX_X_HOST = int(os.getenv('PROXY_FIX_X_HOST', '1'))
PROXY_FIX_X_PORT = int(os.getenv('PROXY_FIX_X_PORT', '1'))
PROXY_FIX_X_PREFIX = int(os.getenv('PROXY_FIX_X_PREFIX', '1'))

# Baseline data bootstrap configuration.
# Useful for keeping dashboards populated in production-like demo environments.
BASELINE_DATA_ENABLED = _env_bool('BASELINE_DATA_ENABLED', APP_ENV == 'production')
BASELINE_MIN_MOTORS = int(os.getenv('BASELINE_MIN_MOTORS', '9'))
BASELINE_CRITICAL_TARGET = int(os.getenv('BASELINE_CRITICAL_TARGET', '2'))
BASELINE_DEGRADING_TARGET = int(os.getenv('BASELINE_DEGRADING_TARGET', '3'))
BASELINE_INFO_ALERTS_TARGET = int(os.getenv('BASELINE_INFO_ALERTS_TARGET', '2'))

# CORS Configuration
# In development, allow all origins to support local frontend ports/hosts.
if APP_ENV != 'production':
    CORS_ALLOWED_ORIGINS = '*'
else:
    raw_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '').strip()
    if not raw_cors_origins:
        CORS_ALLOWED_ORIGINS = []
    elif raw_cors_origins == '*':
        CORS_ALLOWED_ORIGINS = '*'
    else:
        CORS_ALLOWED_ORIGINS = [origin.strip() for origin in raw_cors_origins.split(',') if origin.strip()]

# In production, avoid wildcard CORS unless explicitly intended.
if APP_ENV == 'production' and CORS_ALLOWED_ORIGINS == '*':
    CORS_ALLOWED_ORIGINS = []

if APP_ENV == 'production' and os.getenv('DEV_OTP_IN_RESPONSE') is None:
    DEV_OTP_IN_RESPONSE = False

# Logging Configuration
LOG_FILE = os.getenv('LOG_FILE', 'flask_api.log')
LOG_LEVEL_NAME = os.getenv('LOG_LEVEL', 'INFO').strip().upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
LOG_TO_STDOUT = _env_bool('LOG_TO_STDOUT', True)
REQUEST_LOGGING_ENABLED = _env_bool('REQUEST_LOGGING_ENABLED', True)
SECURITY_HEADERS_ENABLED = _env_bool('SECURITY_HEADERS_ENABLED', True)
LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s'


class RequestContextFilter(logging.Filter):
    """Inject request identifier into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.request_id = getattr(g, 'request_id', '-')
        else:
            record.request_id = '-'
        return True

# Logging Setup
def setup_logging():
    """Setup logging configuration."""
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)
    context_filter = RequestContextFilter()

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    root.addHandler(file_handler)

    if LOG_TO_STDOUT:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(context_filter)
        root.addHandler(stream_handler)

    logging.getLogger('werkzeug').setLevel(LOG_LEVEL)

    return logging.getLogger(__name__)


def now_iso() -> str:
    """Get current time in ISO format."""
    return datetime.now().isoformat()
