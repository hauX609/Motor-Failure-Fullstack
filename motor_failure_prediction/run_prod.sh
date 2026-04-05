#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f ".env.production" ]]; then
  echo "Missing .env.production"
  exit 1
fi

cp .env.production .env

api_key_value="$(grep '^MOTOR_API_KEY=' .env | cut -d'=' -f2-)"
if [[ -z "$api_key_value" || "$api_key_value" == "prod-long-random-secret" ]]; then
  echo "Invalid MOTOR_API_KEY in .env.production. Set a real secret before running production profile."
  exit 1
fi

cors_value="$(grep '^CORS_ALLOWED_ORIGINS=' .env | cut -d'=' -f2-)"
if [[ -z "$cors_value" || "$cors_value" == "*" ]]; then
  echo "Invalid CORS_ALLOWED_ORIGINS for production. Set explicit frontend domain(s)."
  exit 1
fi

echo "Using production environment (.env.production -> .env)"
python3 database_setup.py

generator_pid=""

cleanup() {
  if [[ -n "$generator_pid" ]] && kill -0 "$generator_pid" >/dev/null 2>&1; then
    echo "Stopping data generator (pid: $generator_pid)"
    kill "$generator_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

if [[ "${RUN_DATA_GENERATOR:-false}" == "true" ]]; then
  echo "Starting data generator in background"
  python3 data_generator.py &
  generator_pid=$!
fi

bind_host="${FLASK_HOST:-0.0.0.0}"
bind_port="${FLASK_PORT:-5001}"
workers="${GUNICORN_WORKERS:-3}"
threads="${GUNICORN_THREADS:-2}"
timeout="${GUNICORN_TIMEOUT:-120}"

if ! command -v gunicorn >/dev/null 2>&1; then
  echo "gunicorn is not installed. Install dependencies first (pip install -r requirements.txt)."
  exit 1
fi

echo "Starting production server with gunicorn on ${bind_host}:${bind_port}"
gunicorn \
  --bind "${bind_host}:${bind_port}" \
  --workers "${workers}" \
  --threads "${threads}" \
  --timeout "${timeout}" \
  --access-logfile - \
  --error-logfile - \
  app:app
