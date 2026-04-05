"""
Motor Failure Prediction System - Refactored Architecture
=========================================================

This document describes the new modular, class-based architecture of the motor
failure prediction system.

## Project Structure

├── app.py                          # Main Flask application (simplified)
├── config.py                       # Configuration and constants
├── database_setup.py               # Database initialization
├── data_generator.py               # Sensor data generator
│
├── models/                         # Machine learning and data layer
│   ├── __init__.py
│   ├── database.py                # DatabaseManager class for DB operations
│   └── ml_model.py                # MLModelManager class for model management
│
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py            # AuthenticationService class for OTP/auth
│   ├── email_service.py           # EmailService class for SMTP operations
│   ├── motor_service.py           # MotorService class for motor CRUD
│   ├── alert_service.py           # AlertService class for alert management
│   ├── prediction_service.py      # PredictionService class for predictions
│   └── insight_service.py         # InsightService class for analytics
│
├── routes/                         # API endpoints (Flask blueprints)
│   ├── __init__.py
│   ├── decorators.py              # api_key_required decorator
│   ├── auth_routes.py             # Authentication endpoints
│   ├── motor_routes.py            # Motor CRUD endpoints
│   ├── alert_routes.py            # Alert management endpoints
│   ├── insight_routes.py          # Analytics endpoints
│   └── prediction_routes.py       # Prediction endpoints
│
└── utils/                          # Utilities and helpers
    ├── __init__.py
    ├── validators.py              # Validator class for input validation
    └── errors.py                  # Custom exception classes


## Key Improvements

### 1. **Separation of Concerns**
   - UI Layer: `routes/` - Flask blueprints handle HTTP requests/responses
   - Business Logic: `services/` - Core functionality in service classes
   - Data Layer: `models/` - Database and ML model management
   - Utilities: `utils/` - Validation, errors, and helpers
   - Configuration: `config.py` - Centralized constants and env vars

### 2. **Class-Based Design**
   - **DatabaseManager**: Manages all database connections and queries
   - **MLModelManager**: Loads, caches, and manages ML models
   - **AuthenticationService**: Handles password hashing, OTP, sessions
   - **EmailService**: SMTP configuration and email delivery
   - **MotorService**: Motor CRUD and status management
   - **AlertService**: Alert creation, retrieval, and notifications
   - **PredictionService**: ML inference and prediction logic
   - **InsightService**: Analytics and dashboard data generation
   - **Validator**: Input validation for all data types

### 3. **Error Handling**
   Custom exception hierarchy for consistent, semantic error handling:
   - MotorMonitoringError (base)
   - ValidationError (400)
   - AuthenticationError (401)
   - AuthorizationError (403)
   - NotFoundError (404)
   - ConflictError (409)
   - RateLimitError (429)
   - ServiceUnavailableError (503)
   - DatabaseError (500)

### 4. **Global Service Instances**
   Singleton instances are created in each service module:
   - `db_manager` from models.database
   - `ml_manager` from models.ml_model
   - `auth_service` from services.auth_service
   - `email_service` from services.email_service
   - `motor_service` from services.motor_service
   - `alert_service` from services.alert_service
   - `prediction_service` from services.prediction_service
   - `insight_service` from services.insight_service

   All services are imported and used by routes and other services.


## API Endpoints

### Authentication (`/auth/`)
```
POST   /auth/register       - Register new user
POST   /auth/login          - Login with password → receive OTP
POST   /auth/resend-otp     - Resend OTP with rate limiting
POST   /auth/verify-otp     - Verify OTP → receive bearer token
POST   /auth/logout         - Revoke bearer token
GET    /auth/me             - Get current user info
```

### Motors (`/motors/`)
```
GET    /motors              - List all active motors
POST   /motors              - Create new motor
DELETE /motors/<id>         - Delete/deactivate motor
POST   /motors/<id>/reactivate - Reactivate deactivated motor
GET    /motors/readings/latest   - Latest readings for all motors
GET    /motors/<id>/readings     - Historical readings for motor
```

### Predictions (`/predict/`)
```
GET    /health              - System health check
GET    /predict/<id>        - Predict for single motor
POST   /predict/batch       - Batch predict for multiple motors
POST   /predict/all         - Predict for all active motors
GET    /explain/status/<id> - Explain status prediction (SHAP)
GET    /explain/rul/<id>    - Explain RUL prediction (SHAP)
```

### Alerts (`/alerts/`)
```
GET    /alerts              - Get alerts (with filtering)
POST   /alerts/<id>/ack     - Acknowledge single alert
POST   /alerts/batch/ack    - Batch acknowledge alerts
```

### Insights (`/insights/`)
```
GET    /insights/status-distribution     - Motor status distribution
GET    /insights/alerts-trend            - Daily alerts trend
GET    /insights/sensor-trend/<id>       - Sensor time series + stats
GET    /insights/fleet-overview          - KPI counters
```


## Error Handling Pattern

All services follow this error handling pattern:

```python
class MyService:
    @staticmethod
    def my_operation(param):
        try:
            # Validate inputs
            if not Validator.validate_something(param):
                raise ValidationError("Invalid input")
            
            # Perform operation
            result = perform_operation(param)
            
            return result
        
        except ValidationError:
            raise  # Let route handler catch it
        except DatabaseError:
            raise  # Let route handler catch it
        except Exception as e:
            logger.error(f"Error: {e}")
            raise DatabaseError(f"Operation failed: {str(e)}")
```

Routes catch custom exceptions and return appropriate HTTP responses:

```python
@route.route('/endpoint', methods=['POST'])
@api_key_required
def endpoint():
    try:
        result = my_service.my_operation(param)
        return jsonify(result), 200
    except ValidationError as e:
        return jsonify({'error': e.message}), e.status_code
    except DatabaseError as e:
        return jsonify({'error': e.message}), e.status_code
    except Exception as e:
        logger.error(f"Endpoint error: {e}")
        return jsonify({'error': 'Operation failed'}), 500
```


## Configuration

All configuration is in `config.py` and environment variables:

```python
# Database
DB_FILE = "motors.db"
DB_TIMEOUT = 30

# API Key
SECRET_API_KEY = os.getenv('MOTOR_API_KEY', "...")

# ML Model
REQUIRED_SEQUENCE_LENGTH = 50
STATUS_MAP = {0: 'Optimal', 1: 'Degrading', 2: 'Critical'}

# Authentication
OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', '10'))
SESSION_EXPIRY_HOURS = int(os.getenv('SESSION_EXPIRY_HOURS', '12'))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv('OTP_RESEND_COOLDOWN_SECONDS', '60'))
OTP_MAX_REQUESTS_PER_HOUR = int(os.getenv('OTP_MAX_REQUESTS_PER_HOUR', '5'))

# Email
ALERT_EMAIL_ENABLED = os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_FROM = os.getenv('SMTP_FROM_EMAIL', SMTP_USER)
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
DEV_OTP_IN_RESPONSE = os.getenv('DEV_OTP_IN_RESPONSE', 'true').lower() == 'true'

# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5001
FLASK_THREADED = True
```


## Running the Application

```bash
# Activate conda environment
conda activate motorfailure

# Initialize database (one-time)
python database_setup.py

# Start data generator (in separate terminal)
python data_generator.py

# Start Flask server
python app.py
```

Server runs on `http://localhost:5001`

Endpoints:
- Health check: `GET http://localhost:5001/health`
- Auth: `POST http://localhost:5001/auth/register`
- Predict: `GET http://localhost:5001/predict/<motor_id>`


## Testing

```bash
# Test OTP flow
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"password123"}'

# Login to get OTP
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"test@example.com","password":"password123"}'

# Verify OTP to get token
curl -X POST http://localhost:5001/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","otp":"123456"}'

# Use bearer token
curl -X GET http://localhost:5001/predict/motor_1 \
  -H "Authorization: Bearer <token>"
```


## Database Schema

The system uses SQLite3 with these main tables:

- **motors**: Motor metadata and current status
- **sensor_readings**: Time-series sensor data
- **alerts**: Alert history with severity
- **users**: User accounts for OTP-based login
- **otp_codes**: OTP records with expiration
- **auth_sessions**: Bearer token sessions


## Key Features

### 1. **Authentication & Security**
   - Password hashing: PBKDF2-HMAC-SHA256 (100k iterations, per-user salt)
   - OTP: 6-digit codes, 10-minute expiry, rate-limited
   - Bearer tokens: 48-byte secure tokens, configurable expiry
   - Dual auth mode: Legacy API key + new OTP-based bearer tokens

### 2. **Error Handling**
   - Custom exception hierarchy
   - Consistent error response format
   - Proper HTTP status codes
   - Detailed logging on all errors
   - SQL injection prevention via parameterized queries

### 3. **Email Notifications**
   - SMTP configurable (Gmail, SES, Mailgun, custom)
   - OTP delivery
   - Motor degradation alerts
   - Batch alert emails
   - Dev mode fallback (returns OTP in response)

### 4. **Motor Management**
   - Self-service CRUD operations
   - Soft-delete with reactivation
   - Hard-delete option
   - Automatic generator sync on create/delete
   - Status tracking and history

### 5. **Predictions**
   - Single motor predictions
   - Batch predictions (up to 100 motors)
   - Predict all active motors
   - SHAP-based explanations for status and RUL
   - Alert generation on degradation

### 6. **Analytics & Dashboards**
   - Status distribution charts
   - Daily alerts trend
   - Sensor time-series + statistics
   - Fleet KPI counters
   - Historical readings with pagination

### 7. **Rate Limiting**
   - OTP resend: 60-second cooldown + 5/hour max
   - API: Query limits on batch operations
   - Pagination: Max 1000 records per request


## Development Guidelines

### Adding a New Service
1. Create file: `services/my_service.py`
2. Define service class with `@staticmethod` methods
3. Create global instance: `my_service = MyService()`
4. Import in routes and use

### Adding a New Route
1. Create file: `routes/my_routes.py`
2. Create blueprint: `my_bp = Blueprint(...)`
3. Add routes with `@my_bp.route()` decorator
4. Use `@api_key_required` for protected endpoints
5. Register in `app.py`: `app.register_blueprint(my_bp)`

### Adding Validation
1. Add method to `Validator` class in `utils/validators.py`
2. Use in services: `if not Validator.validate_something(data):`
3. Raise `ValidationError` on failure

### Adding Error Type
1. Define in `utils/errors.py`
2. Extend `MotorMonitoringError`
3. Set appropriate `status_code`
4. Catch and handle in routes


## Migration from Old Code

Old monolithic `app.py` (3100 lines) → New modular structure:

- Validation functions → `utils/validators.py:Validator` class
- Auth helpers → `services/auth_service.py:AuthenticationService` class
- Email sending → `services/email_service.py:EmailService` class
- Database queries → `models/database.py:DatabaseManager` class
- ML model operations → `models/ml_model.py:MLModelManager` class
- Motor operations → `services/motor_service.py:MotorService` class
- Alert operations → `services/alert_service.py:AlertService` class
- Prediction functions → `services/prediction_service.py:PredictionService` class
- Insight generation → `services/insight_service.py:InsightService` class
- Auth decorator → `routes/decorators.py:api_key_required` decorator
- All endpoints → Organized in `routes/` as blueprints

Error handling, logging, and exception hierarchy remain consistent!


## Performance Optimizations

- **Database**: Connection pooling via context manager, parameterized queries
- **ML Model**: Thread-safe predictions with model_lock, batch processing
- **Caching**: Scaler transformations cached in MLModelManager
- **Pagination**: All list endpoints support limit parameter
- **Batch Operations**: Bulk inserts/updates for efficiency
- **SHAP Explainers**: Lazy-loaded, optional initialization


## Security Measures

✅ Parameterized SQL queries (prevents SQL injection)
✅ PBKDF2 password hashing (strong, configurable)
✅ OTP rate limiting (cooldown + hourly max)
✅ Bearer token expiration (configurable)
✅ SSL/TLS support for SMTP
✅ Input validation on all endpoints
✅ Logging of auth failures
✅ Dev mode override (DEV_OTP_IN_RESPONSE) for local testing
✅ Foreign key constraints enabled in SQLite
✅ Const-time password comparison (hmac.compare_digest)


## Next Steps

1. **Test all endpoints** with curl or Postman
2. **Configure SMTP** for production email delivery
3. **Set environment variables** for sensitive config
4. **Monitor logs** in `flask_api.log`
5. **Scale horizontally** with multiple worker processes (gunicorn)
6. **Add request rate limiting** with Flask-Limiter
7. **Implement CORS** if frontend is separate domain
8. **Add API versioning** (/api/v1/, /api/v2/)
9. **Set up monitoring** with Prometheus/Grafana
10. **Add unit tests** with pytest


## Troubleshooting

**ImportError: No module named...?**
→ Check all service files are importing from correct modules
→ Verify `from ... import ...` paths

**ValidationError not caught in route?**
→ Make sure route catches exception before returning
→ Check exception is imported

**Database locked?**
→ Ensure connections closed in finally block
→ Use context manager (with db_manager.get_connection())

**Model not loading?**
→ Check ml_manager.is_ready() before prediction
→ Verify model files exist in project root

**OTP not sending?**
→ Check SMTP_* env vars configured
→ Enable DEV_OTP_IN_RESPONSE=true to debug

**SHAP explainers unavailable?**
→ Check shap_background.pkl file exists
→ ml_manager.has_explainers() returns False if file missing
"""
