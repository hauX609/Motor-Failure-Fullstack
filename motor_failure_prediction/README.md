# Motor Failure Backend

Flask API for motor monitoring, alerts, insights, and prediction workflows.

## Run (Development)
```bash
cp .env.example .env.development
pip install -r requirements.txt
./run_dev.sh
```

## Run (Production Profile)
```bash
# Prepare .env.production with real secrets and domains
./run_prod.sh
```

## Core Endpoints
- `/auth/*` - login and OTP flows
- `/motors/*` - motor CRUD and readings
- `/alerts/*` - alert listing and acknowledge actions
- `/insights/*` - dashboard analytics and trend data
- `/predict/*` - model inference endpoints

## Notes
- SQLite database file: `motors.db`
- Environment controls are loaded from `.env` (copied by run scripts)
- Keep `.env.production` secrets out of git
