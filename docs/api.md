# API

Base path: `/api/v1`  
Auth: header `X-API-Key: ratescope-demo-key` (or query `api_key` for SSE).

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/hotels` | Optional `city` |
| GET | `/hotels/{id}/rates` | Optional `stay_date` |
| GET | `/rooms/{id}/price-history` | Cursor not required; time series |
| GET | `/alerts` | Filters + cursor pagination (`cursor`, `limit`) |
| PATCH | `/alerts/{id}` | `{ "status": "ACKNOWLEDGED" \| "RESOLVED" }` |
| GET | `/parity/report` | Supplier pair spreads + city heatmap |
| GET | `/stats/daily` | Analytics snapshots |
| GET | `/stream/alerts` | Server-Sent Events |
| POST | `/ask` | `{ "question": "..." }` |
| GET | `/health/live` | Liveness, no auth |
| GET | `/health/ready` | Postgres + Redis |

Errors:

```json
{ "error": { "code": "http_error", "message": "..." } }
```
