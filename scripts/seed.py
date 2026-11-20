#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.analytics.daily import compute_for_date
from app.core.db import SessionLocal, engine
from app.core.logging import setup_logging
from app.models.entities import Base
from app.seed_data import seed_history, seed_reference
from datetime import date


def main() -> None:
    setup_logging()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_reference(db)
        n = seed_history(db)
        compute_for_date(db, date.today())
        db.commit()
        print(f"seeded reference data and {n} historical events")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
