# Test plan

Automated (CI):

- Unit: parity classification, z-score spikes/drops, Pydantic event validation, FX conversion
- Integration: store event, duplicate suppression, DLQ, auto-resolve parity, anomaly cooldown, REST auth and alert patch
- Frontend: production `npm run build`

Manual after `docker compose up`:

1. Open http://localhost:8080 — KPI counts are non-zero after seed
2. Live Alerts populate; Ack and Resolve persist after refresh
3. Price Explorer draws supplier lines from `/rooms/{id}/price-history`
4. Parity page shows pairs/heatmap
5. Ask RateScope returns filters + results without an OpenAI key
6. System Health shows postgres/redis up
7. Invalid simulator `MALFORMED` events increase DLQ on `/health/system`
