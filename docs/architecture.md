# Architecture

RateScope is a **modular monolith**. One FastAPI codebase exposes the HTTP API; the same image runs a Kafka consumer worker, a supplier simulator, and a Pandas analytics job.

```
Simulator → Kafka (Redpanda) → Worker (validate, FX, store, detect)
                                      ↓
                              PostgreSQL ← REST API ← React dashboard
                                      ↑
                                    Redis cache
```

## Components

- `app/pipeline` — Kafka publish/consume, validation, USD normalization, idempotent writes, DLQ
- `app/detection` — parity spread and rolling z-score anomalies
- `app/analytics` — daily average, median, volatility, demand score
- `app/llm` — Ask RateScope: JSON filters only, schema validation, heuristic fallback
- `app/api` — versioned REST (`/api/v1`), API key, rate limit, SSE alerts

## Data

Hotels, rooms, suppliers, rate events, alerts, DLQ rows, daily stats, and exchange rates. Hot paths are indexed (`event_id`, city, stay date, alert status).

## Reliability

Retries with exponential backoff on the retry topic, DLQ persistence, graceful shutdown of the consumer, structured JSON logs, `/health/live` and `/health/ready`, Prometheus metrics.
