from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.detection.parity import SupplierPrice, detect_parity
from app.models.entities import Alert, Hotel, RateEvent, Room, Supplier


def build_parity_report(db: Session, settings: Settings, city: str | None = None) -> dict:
    suppliers = {s.id: s.code for s in db.execute(select(Supplier)).scalars().all()}
    hotels = {h.id: h for h in db.execute(select(Hotel)).scalars().all()}
    stmt = select(RateEvent).order_by(RateEvent.received_at.desc()).limit(4000)
    if city:
        stmt = stmt.where(RateEvent.city.ilike(city))
    events = db.execute(stmt).scalars().all()

    latest: dict[tuple, dict[int, RateEvent]] = defaultdict(dict)
    for ev in events:
        key = (ev.hotel_id, ev.room_id, ev.stay_date, ev.cancellation_policy)
        if ev.supplier_id not in latest[key]:
            latest[key][ev.supplier_id] = ev

    pairs = []
    city_spreads: dict[str, list[float]] = defaultdict(list)
    for key, by_sup in latest.items():
        hotel_id = key[0]
        hotel = hotels.get(hotel_id)
        prices = [
            SupplierPrice(suppliers[sid], ev.price_usd)
            for sid, ev in by_sup.items()
            if sid in suppliers
        ]
        result = detect_parity(prices, settings.parity_threshold_pct, settings.parity_medium_pct, settings.parity_high_pct)
        if not result or not result.violated:
            continue
        hcity = hotel.city if hotel else "Unknown"
        city_spreads[hcity].append(result.spread_pct)
        for p in result.pairs:
            if p["spread_pct"] >= settings.parity_threshold_pct:
                pairs.append(
                    {
                        **p,
                        "hotel_id": hotel_id,
                        "city": hcity,
                        "stay_date": key[2].isoformat(),
                    }
                )

    heatmap = [
        {
            "city": c,
            "avg_spread_pct": round(sum(vals) / len(vals), 2),
            "violations": len(vals),
            "max_spread_pct": round(max(vals), 2),
        }
        for c, vals in sorted(city_spreads.items())
    ]
    open_alerts = db.execute(select(Alert).where(Alert.alert_type == "PARITY", Alert.status.in_(["OPEN", "ACKNOWLEDGED"]))).scalars().all()

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "threshold_pct": settings.parity_threshold_pct,
        "pairs": pairs[:200],
        "city_heatmap": heatmap,
        "open_alerts": len(open_alerts),
    }
