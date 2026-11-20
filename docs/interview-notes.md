# Interview notes

## Why this design

Agoda’s rate stack is about **correct prices under high event volume**, not microservices for their own sake. RateScope keeps one deployable backend with explicit modules: ingestion, detection, API, analytics, LLM-as-filter.

## Talking points

- **Idempotency:** unique `event_id` so Kafka redelivery does not double-count rates.
- **Parity:** same hotel, room, stay date, cancellation policy; spread vs cheapest; auto-resolve when the market heals.
- **Anomalies:** rolling mean/std and z-score, cooldown so a spike does not page you every second.
- **LLM safety:** the model cannot touch SQL. It emits JSON; Pydantic enumerations reject prompt-injected fields.
- **Ops:** live/ready probes, request IDs, Prometheus, DLQ, retries with backoff.

## Tradeoffs I would revisit at Agoda scale

- Partition Kafka by `hotel_id` for ordered per-hotel processing
- Replace SSE polling with a proper pub/sub if fan-out grows
- Move detection to stream-time window stores (Flink / Kafka Streams) instead of SQL windows
- Separate read models for the dashboard
