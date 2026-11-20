from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings
from app.core.db import SessionLocal, engine
from app.models.entities import Base
from app.pipeline.processor import process_payload
from app.seed_data import seed_history, seed_reference
from app.simulator.engine import next_batch

logger = logging.getLogger(__name__)


def bootstrap_data() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_reference(db)
        n = seed_history(db)
        db.commit()
        logger.info("bootstrap_ok", extra={"request_id": "-", "history": n})
    except Exception:
        db.rollback()
        logger.exception("bootstrap_failed")
        raise
    finally:
        db.close()


async def inline_simulator(settings: Settings) -> None:
    tick = 0
    interval = max(0.4, settings.simulator_interval_seconds / max(settings.simulator_speed, 0.1))
    while True:
        db = SessionLocal()
        try:
            events = next_batch(db, tick, burst=False)
            for ev in events:
                process_payload(db, ev, settings)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("inline_simulator_tick_failed")
        finally:
            db.close()
        tick += 1
        await asyncio.sleep(interval)
