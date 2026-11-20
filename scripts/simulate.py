#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.pipeline.kafka import kafka_ready, publish_event, stop_kafka
from app.pipeline.processor import process_payload
from app.simulator.engine import next_batch


async def run(duration: float, speed: float, interval: float) -> None:
    setup_logging()
    settings = get_settings()
    use_kafka = await kafka_ready(settings)
    start = time.time()
    tick = 0
    deadline = start + duration if duration > 0 else None
    while True:
        db = SessionLocal()
        try:
            events = next_batch(db, tick, burst=False)
            if use_kafka:
                for ev in events:
                    await publish_event(settings.kafka_topic_rates, ev, key=str(ev.get("hotel_id")))
            else:
                for ev in events:
                    process_payload(db, ev, settings)
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        tick += 1
        if deadline and time.time() >= deadline:
            break
        await asyncio.sleep(max(0.2, interval / max(speed, 0.1)))
    await stop_kafka()


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="RateScope supplier simulator")
    parser.add_argument("--duration", type=float, default=0, help="Seconds to run; 0 = forever")
    parser.add_argument("--speed", type=float, default=settings.simulator_speed)
    parser.add_argument("--interval", type=float, default=settings.simulator_interval_seconds)
    args = parser.parse_args()
    asyncio.run(run(args.duration, args.speed, args.interval))


if __name__ == "__main__":
    main()
