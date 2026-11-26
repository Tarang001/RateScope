# RateScope

Hotel rate intelligence platform for monitoring supplier prices, detecting rate parity breaks, and flagging anomalies. Built as a modular monolith for a Software Engineering internship application.

## What it does

- Simulates live hotel rates from **Agoda**, **Booking.com**, and **Expedia**
- Ingests events through **Kafka (Redpanda)**, validates them, converts currencies to USD, and stores them in **PostgreSQL**
- Deduplicates by `event_id` and sends invalid payloads to a **DLQ**
- Detects **parity violations** and **price spikes/drops**
- Serves a React dashboard with live alerts, charts, parity analysis, and Ask RateScope

## Run on localhost (no Docker)

Two terminals:

```bash
cp .env.example .env

# Terminal 1 — API (seeds data and generates live rates if Kafka is not running)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — dashboard
cd frontend
npm install
npm run dev
```

| Surface | URL |
| --- | --- |
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

The API uses SQLite by default, seeds hotels, and runs an in-process supplier simulator so the UI has real rates, alerts, and charts.

## Docker (optional full stack)

Requires Docker Desktop. Compose starts Postgres, Redis, Redpanda, API, worker, simulator, frontend, Prometheus, and Grafana.

```bash
docker compose up --build
```

Then dashboard is http://localhost:8080 and API is http://localhost:8000. Grafana: http://localhost:3001 (admin / admin).

## Tests and frontend build (without Docker)

```bash
# backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q

# frontend
cd ../frontend
npm install
npm run build
```

## Ask RateScope

Works **without** an LLM key using a deterministic parser. To enable model-backed filter generation:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

The LLM is only allowed to emit JSON filters. Those filters are validated and mapped to normal queries. It never generates or executes SQL.

## Project layout

```
backend/     FastAPI API, worker, detection, analytics, LLM
frontend/    React + Vite + Tailwind dashboard
infra/       Prometheus and Grafana
scripts/     seed.py, simulate.py, run_analytics.py
docs/        architecture, API, deployment, tests, interview notes
```

## Deploying publicly

See [docs/deployment.md](docs/deployment.md) for Vercel (frontend), Render (backend), managed PostgreSQL/Redis, and cloud Kafka. Local Docker services are **not** production infrastructure.

## License

Provided as a portfolio/demo project.
