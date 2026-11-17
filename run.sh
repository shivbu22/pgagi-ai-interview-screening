#!/usr/bin/env bash
# Screenwise — one-command local run.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r backend/requirements.txt
fi
if [ ! -d frontend/dist ]; then
  (cd frontend && npm install && npm run build)
fi
echo "Screenwise running at http://localhost:${PORT:-8410}"
cd backend
exec ../.venv/bin/uvicorn app.main:app --port "${PORT:-8410}"
