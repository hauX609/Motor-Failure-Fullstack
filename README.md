# Motor Failure Fullstack

End-to-end motor health monitoring and failure prediction platform.

This monorepo contains:
- `motor_failure/` - React + Vite frontend dashboard
- `motor_failure_prediction/` - Flask backend, prediction services, alerts, and simulator

## Features
- Live fleet dashboard (status distribution, alerts trend, latest alerts)
- Motor lifecycle management (add, deactivate/reactivate, detail pages)
- Prediction endpoints with status + RUL outputs
- Alerting pipeline with severity and acknowledge flows
- Production profiles with safety guards and environment-based behavior

## Repository Structure
```text
motor_failure_fullstack/
├── motor_failure/                 # Frontend app (React + TypeScript + Vite)
└── motor_failure_prediction/      # Backend API (Flask + SQLite + ML assets)
```

## Prerequisites
- Node.js 18+
- npm 9+
- Python 3.10+
- pip

## Quick Start (Development)

### 1. Backend
```bash
cd motor_failure_prediction
cp .env.example .env.development
pip install -r requirements.txt
./run_dev.sh
```

### 2. Frontend
In a second terminal:
```bash
cd motor_failure
cp .env.example .env.development
npm install
npm run dev
```

Frontend: `http://localhost:8080` (or your configured Vite port)  
Backend: `http://localhost:5001`

## Production Profile

### Backend
```bash
cd motor_failure_prediction
# Create .env.production with real secrets and CORS values
./run_prod.sh
```

### Frontend
```bash
cd motor_failure
# Create .env.production with real API base URL
npm run build
npm run preview
```

## Environment Files
- Frontend template: `motor_failure/.env.example`
- Backend template: `motor_failure_prediction/.env.example`

Never commit real secrets (`MOTOR_API_KEY`, SMTP credentials, etc).

## Testing and Quality

Frontend:
```bash
cd motor_failure
npm run build
```

Backend syntax check:
```bash
cd motor_failure_prediction
python3 -m py_compile app.py
```

## License
MIT License. See `LICENSE`.

## Contributing
See `CONTRIBUTING.md` for branch and PR guidelines.

## Repository Standards
- Security policy: `SECURITY.md`
- Issue templates: `.github/ISSUE_TEMPLATE/`
- PR template: `.github/pull_request_template.md`
- Release process: `RELEASE_CHECKLIST.md`
