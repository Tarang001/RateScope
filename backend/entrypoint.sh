#!/bin/sh
set -e
cd /app/backend
alembic upgrade head
python /app/scripts/seed.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
