from prometheus_client import Counter, Gauge, Histogram, generate_latest

EVENTS_PROCESSED = Counter("ratescope_events_processed_total", "Valid events stored", ["status"])
EVENTS_INVALID = Counter("ratescope_events_invalid_total", "Invalid events sent to DLQ")
PROCESSING_LATENCY = Histogram(
    "ratescope_processing_latency_seconds",
    "Event processing latency",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
ALERTS_CREATED = Counter("ratescope_alerts_created_total", "Alerts created", ["type", "severity"])
CONSUMER_LAG = Gauge("ratescope_consumer_lag", "Approximate consumer lag")
DLQ_COUNT = Gauge("ratescope_dlq_count", "DLQ row count")
API_HEALTH = Gauge("ratescope_api_up", "API process up")


def metrics_payload() -> bytes:
    API_HEALTH.set(1)
    return generate_latest()
