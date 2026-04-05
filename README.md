# Motor Failure Fullstack

This repository contains:
- `motor_failure/` - React + Vite frontend
- `motor_failure_prediction/` - Flask backend + simulator

## Quick Start

Frontend:
1. `cd motor_failure`
2. `cp .env.example .env.development`
3. `npm install`
4. `npm run dev`

Backend (development):
1. `cd motor_failure_prediction`
2. `cp .env.example .env.development`
3. `pip install -r requirements.txt`
4. `./run_dev.sh`

Backend (production profile):
1. `cd motor_failure_prediction`
2. create `.env.production` with real values
3. `./run_prod.sh`
