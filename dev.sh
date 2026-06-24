#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down..."
  if [[ -n "${BACKEND_PID:-}" || -n "${FRONTEND_PID:-}" ]]; then
    kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
    wait "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "$ROOT/backend"
echo "Applying backend migrations..."
.venv/bin/alembic upgrade heads

echo "Starting backend..."
.venv/bin/uvicorn fantasy.main:app --reload &
BACKEND_PID=$!

echo "Starting frontend..."
cd "$ROOT/frontend"
pnpm dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID | Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both."

wait
