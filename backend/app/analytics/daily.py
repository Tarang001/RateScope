from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.detection.parity import SupplierPrice, detect_parity
from app.models.entities import Alert, DailyStat, Hotel, RateEvent, Supplier


def compute_for_date(db: Session, stat_date: date) -> int:
    settings = get_settings()
    hotels = {h.id: h for h in db.execute(select(Hotel)).scalars().all()}
    suppliers = {s.id: s.code for s in db.execute(select(Supplier)).scalars().all()}
    events = db.execute(select(RateEvent).where(RateEvent.stay_date == stat_date)).scalars().all()
    if not events:
        events = db.execute(
            select(RateEvent).where(RateEvent.received_at >= stat_date, RateEvent.received_at < stat_date + timedelta(days=1))
        ).scalars().all()
    if not events:
        return 0

    df = pd.DataFrame(
        [
            {
                "hotel_id": e.hotel_id,
                "room_id": e.room_id,
                "supplier_id": e.supplier_id,
                "price_usd": e.price_usd,
                "availability": e.availability,
                "received_at": e.received_at,
                "stay_date": e.stay_date,
                "cancellation_policy": e.cancellation_policy,
            }
            for e in events
        ]
    )
    written = 0
    db.execute(delete(DailyStat).where(DailyStat.stat_date == stat_date))

    for hotel_id, group in df.groupby("hotel_id"):
        hotel = hotels.get(int(hotel_id))
        if hotel is None:
            continue
        prices = group["price_usd"].astype(float).tolist()
        avg = float(np.mean(prices))
        median = float(np.median(prices))
        volatility = float(np.std(prices, ddof=1)) if len(prices) > 1 else 0.0

        violations = 0
        for (room_id, stay, policy), g2 in group.groupby(["room_id", "stay_date", "cancellation_policy"]):
            latest = g2.sort_values("received_at").groupby("supplier_id").tail(1)
            plist = [
                SupplierPrice(suppliers.get(int(r.supplier_id), str(r.supplier_id)), float(r.price_usd))
                for r in latest.itertuples()
            ]
            result = detect_parity(plist, settings.parity_threshold_pct, settings.parity_medium_pct, settings.parity_high_pct)
            if result and result.violated:
                violations += 1

        avail_delta = float(group["availability"].astype(float).std()) if len(group) > 1 else 0.0
        price_move = volatility / avg if avg else 0.0
        demand = min(100.0, round((avail_delta * 2) + (price_move * 40), 2))

        db.add(
            DailyStat(
                stat_date=stat_date,
                hotel_id=int(hotel_id),
                city=hotel.city,
                avg_price=round(avg, 2),
                median_price=round(median, 2),
                volatility=round(volatility, 2),
                parity_violations=violations,
                demand_score=demand,
                event_count=len(group),
            )
        )
        written += 1
    db.flush()
    return written


def compute_range(db: Session, start: date, end: date) -> int:
    total = 0
    cur = start
    while cur <= end:
        total += compute_for_date(db, cur)
        cur += timedelta(days=1)
    return total
