# Deployment

Do **not** point production at your laptop Docker Compose stack. Use managed services.

## Frontend (Vercel)

1. Set the Vercel root to `frontend`.
2. Environment variables:
   - `VITE_API_BASE_URL` = `https://<your-backend>/api/v1`
   - `VITE_API_KEY` = a strong key (not the demo key)
3. Build command: `npm run build`
4. Output: `dist`

## Backend (Render or any Docker host)

Simplest public demo (no Kafka required): set `DEMO_MODE=true`. The API seeds data and generates supplier events in-process.

1. Use `backend/Dockerfile` with build context at the repo root.
2. Start command: `alembic upgrade head && python /app/scripts/seed.py && uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. Optional second process `python -m app.worker` only if you have Kafka.
4. Environment:
   - `DATABASE_URL` — managed PostgreSQL (`postgresql+psycopg2://...`)
   - `REDIS_URL` — managed Redis (optional; cache degrades if missing)
   - `KAFKA_BOOTSTRAP_SERVERS` — optional; without Kafka, demo simulator still runs
   - `API_KEY`, `CORS_ORIGINS` (must include your Vercel URL)
   - `DEMO_MODE=true`
   - `OPENAI_API_KEY` optional
   - `APP_ENV=production`

## Kafka

Create topics `supplier.rates`, `supplier.rates.retry`, `supplier.rates.dlq`. Point `KAFKA_BOOTSTRAP_SERVERS` at the cloud bootstrap URL. The simulator can run as a cron job or one-off worker.

## Analytics

Schedule `python /app/scripts/run_analytics.py --date YYYY-MM-DD` or `--start` / `--end`.
