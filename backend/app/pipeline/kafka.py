from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
from aiokafka.errors import KafkaError

from app.core.config import Settings, get_settings
from app.core.db import SessionLocal
from app.core.metrics import CONSUMER_LAG
from app.pipeline.processor import process_payload, record_metric, send_dlq

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None
_stop = asyncio.Event()


async def get_producer(settings: Settings | None = None) -> AIOKafkaProducer:
    global _producer
    settings = settings or get_settings()
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
        )
        await _producer.start()
    return _producer


async def publish_event(topic: str, payload: dict[str, Any], key: str | None = None) -> None:
    producer = await get_producer()
    await producer.send_and_wait(topic, payload, key=key.encode() if key else None)


async def stop_kafka() -> None:
    global _producer
    _stop.set()
    if _producer is not None:
        await _producer.stop()
        _producer = None


async def kafka_ready(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    try:
        consumer = AIOKafkaConsumer(bootstrap_servers=settings.kafka_bootstrap_servers, request_timeout_ms=3000)
        await consumer.start()
        await consumer.stop()
        return True
    except Exception:
        return False


async def _publish_dlq(settings: Settings, payload: dict[str, Any], reason: str) -> None:
    try:
        await publish_event(
            settings.kafka_topic_dlq,
            {"reason": reason, "payload": payload},
            key=str(payload.get("event_id", "unknown")),
        )
    except Exception:
        logger.exception("kafka_dlq_publish_failed")


async def consume_loop() -> None:
    settings = get_settings()
    _stop.clear()
    backoff = 1.0
    while not _stop.is_set():
        consumer = AIOKafkaConsumer(
            settings.kafka_topic_rates,
            settings.kafka_topic_retry,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda b: json.loads(b.decode("utf-8")) if b else {},
        )
        try:
            await consumer.start()
            await get_producer(settings)
            backoff = 1.0
            logger.info("kafka_consumer_started", extra={"request_id": "-"})
            async for msg in consumer:
                if _stop.is_set():
                    break
                payload = msg.value if isinstance(msg.value, dict) else {}
                retries = int(payload.get("_retry", 0))
                db = SessionLocal()
                try:
                    result = process_payload(db, payload, settings)
                    db.commit()
                    if result == "dlq":
                        await _publish_dlq(settings, payload, "rejected")
                except Exception as exc:
                    db.rollback()
                    logger.exception("process_failed")
                    if retries < 3:
                        payload["_retry"] = retries + 1
                        try:
                            await asyncio.sleep(min(2**retries, 8))
                            await publish_event(settings.kafka_topic_retry, payload)
                        except KafkaError:
                            logger.exception("retry_publish_failed")
                    else:
                        try:
                            send_dlq(db, payload, f"exception:{exc}", str(payload.get("event_id", "unknown")), retries)
                            db.commit()
                        except Exception:
                            db.rollback()
                        await _publish_dlq(settings, payload, f"exception:{exc}")
                finally:
                    db.close()
                await consumer.commit()
                try:
                    tp = TopicPartition(msg.topic, msg.partition)
                    end = await consumer.end_offsets([tp])
                    lag = max(0, end.get(tp, msg.offset) - msg.offset - 1)
                    CONSUMER_LAG.set(lag)
                    metric_db = SessionLocal()
                    try:
                        record_metric(metric_db, "consumer_lag", float(lag))
                        metric_db.commit()
                    except Exception:
                        metric_db.rollback()
                    finally:
                        metric_db.close()
                except Exception:
                    pass
        except Exception:
            logger.exception("kafka_consumer_loop_error")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        finally:
            try:
                await consumer.stop()
            except Exception:
                pass
