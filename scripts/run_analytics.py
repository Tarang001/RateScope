#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.analytics.daily import compute_for_date, compute_range
from app.core.db import SessionLocal
from app.core.logging import setup_logging


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="RateScope daily analytics")
    parser.add_argument("--date", type=parse_date, default=None)
    parser.add_argument("--start", type=parse_date, default=None)
    parser.add_argument("--end", type=parse_date, default=None)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.start and args.end:
            n = compute_range(db, args.start, args.end)
        else:
            n = compute_for_date(db, args.date or date.today())
        db.commit()
        print(f"wrote {n} daily stat rows")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
