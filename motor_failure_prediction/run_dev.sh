#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f ".env.development" ]]; then
  echo "Missing .env.development"
  exit 1
fi

cp .env.development .env

if grep -q "MOTOR_API_KEY=dev-change-this-to-a-random-secret" .env; then
  echo "Warning: You are using the placeholder MOTOR_API_KEY in .env"
fi

echo "Using development environment (.env.development -> .env)"
python3 database_setup.py

generator_pid=""

cleanup() {
  if [[ -n "$generator_pid" ]] && kill -0 "$generator_pid" >/dev/null 2>&1; then
    echo "Stopping data generator (pid: $generator_pid)"
    kill "$generator_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting data generator in background"
python3 data_generator.py &
generator_pid=$!

echo "Starting development API server"
python3 app.py