from datetime import date, datetime
from typing import Any

from sqlalchemy import String, cast, desc, func, select
from sqlalchemy.orm import Session

from app.models.entities import Alert, DailyStat, DlqEvent, Hotel, RateEvent, Room, Supplier, SystemMetric


def list_hotels(db: Session, city: str | None = None) -> list[Hotel]:
    stmt = select(Hotel).order_by(Hotel.city, Hotel.name)
    if city:
        stmt = stmt.where(Hotel.city.ilike(city))
    return list(db.execute(stmt).scalars().all())


def get_hotel(db: Session, hotel_id: int) -> Hotel | None:
    return db.get(Hotel, hotel_id)


def rooms_for_hotel(db: Session, hotel_id: int) -> list[Room]:
    return list(db.execute(select(Room).where(Room.hotel_id == hotel_id)).scalars().all())


def latest_rates_for_hotel(db: Session, hotel_id: int, stay_date: date | None = None, limit: int = 50) -> list[dict]:
    stmt = (
        select(RateEvent, Supplier.code)
        .join(Supplier, Supplier.id == RateEvent.supplier_id)
        .where(RateEvent.hotel_id == hotel_id)
        .order_by(desc(RateEvent.received_at))
        .limit(limit)
    )
    if stay_date:
        stmt = stmt.where(RateEvent.stay_date == stay_date)
    rows = db.execute(stmt).all()
    return [
        {
            "event_id": ev.event_id,
            "room_id": ev.room_id,
            "supplier_code": code,
            "stay_date": ev.stay_date.isoformat(),
            "price_usd": ev.price_usd,
            "currency": ev.currency,
            "price_original": ev.price_original,
            "availability": ev.availability,
            "cancellation_policy": ev.cancellation_policy,
            "received_at": ev.received_at.isoformat(),
        }
        for ev, code in rows
    ]


def price_history(
    db: Session,
    room_id: int,
    stay_date: date | None = None,
    supplier: str | None = None,
    limit: int = 200,
) -> list[dict]:
    stmt = (
        select(RateEvent, Supplier.code)
        .join(Supplier, Supplier.id == RateEvent.supplier_id)
        .where(RateEvent.room_id == room_id)
        .order_by(RateEvent.received_at.asc())
        .limit(limit)
    )
    if stay_date:
        stmt = stmt.where(RateEvent.stay_date == stay_date)
    if supplier:
        stmt = stmt.where(Supplier.code == supplier.upper())
    rows = db.execute(stmt).all()
    return [
        {
            "received_at": ev.received_at.isoformat(),
            "stay_date": ev.stay_date.isoformat(),
            "supplier_code": code,
            "price_usd": ev.price_usd,
            "availability": ev.availability,
            "scenario": ev.scenario,
        }
        for ev, code in rows
    ]


def list_alerts(
    db: Session,
    city: str | None = None,
    supplier: str | None = None,
    alert_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    cursor: int | None = None,
    limit: int = 25,
) -> tuple[list[Alert], bool]:
    stmt = select(Alert).order_by(desc(Alert.id)).limit(limit + 1)
    if city:
        stmt = stmt.where(Alert.city.ilike(city))
    if alert_type:
        stmt = stmt.where(Alert.alert_type == alert_type.upper())
    if severity:
        stmt = stmt.where(Alert.severity == severity.upper())
    if status:
        stmt = stmt.where(Alert.status == status.upper())
    if cursor:
        stmt = stmt.where(Alert.id < cursor)
    if supplier:
        stmt = stmt.where(cast(Alert.supplier_codes, String).ilike(f'%"{supplier.upper()}"%'))
    rows = list(db.execute(stmt).scalars().all())
    has_more = len(rows) > limit
    return rows[:limit], has_more


def patch_alert(db: Session, alert_id: int, status: str) -> Alert | None:
    alert = db.get(Alert, alert_id)
    if not alert:
        return None
    alert.status = status
    alert.updated_at = datetime.utcnow()
    if status == "RESOLVED":
        alert.resolved_at = datetime.utcnow()
    db.flush()
    return alert


def daily_stats(db: Session, city: str | None = None, start: date | None = None, end: date | None = None) -> list[DailyStat]:
    stmt = select(DailyStat).order_by(desc(DailyStat.stat_date), DailyStat.city)
    if city:
        stmt = stmt.where(DailyStat.city.ilike(city))
    if start:
        stmt = stmt.where(DailyStat.stat_date >= start)
    if end:
        stmt = stmt.where(DailyStat.stat_date <= end)
    return list(db.execute(stmt).scalars().all())


def overview(db: Session) -> dict[str, Any]:
    hotels = db.execute(select(func.count(Hotel.id))).scalar() or 0
    suppliers = db.execute(select(func.count(Supplier.id))).scalar() or 0
    events = db.execute(select(func.count(RateEvent.id))).scalar() or 0
    open_alerts = db.execute(select(func.count(Alert.id)).where(Alert.status.in_(["OPEN", "ACKNOWLEDGED"]))).scalar() or 0
    dlq = db.execute(select(func.count(DlqEvent.id))).scalar() or 0
    recent = db.execute(select(RateEvent).order_by(desc(RateEvent.received_at)).limit(12)).scalars().all()
    return {
        "hotels": hotels,
        "suppliers": suppliers,
        "events_processed": events,
        "active_alerts": open_alerts,
        "dlq_count": dlq,
        "recent": [
            {
                "id": e.id,
                "hotel_id": e.hotel_id,
                "city": e.city,
                "price_usd": e.price_usd,
                "stay_date": e.stay_date.isoformat(),
                "received_at": e.received_at.isoformat(),
                "scenario": e.scenario,
            }
            for e in recent
        ],
    }


def system_health_counts(db: Session) -> dict[str, Any]:
    events = db.execute(select(func.count(RateEvent.id))).scalar() or 0
    dlq = db.execute(select(func.count(DlqEvent.id))).scalar() or 0
    metrics = {m.name: m.value for m in db.execute(select(SystemMetric)).scalars().all()}
    return {
        "events_processed": events,
        "dlq_count": dlq,
        "processing_latency_ms": metrics.get("processing_latency_ms", 0),
        "consumer_lag": metrics.get("consumer_lag", 0),
    }


def hotel_name_map(db: Session) -> dict[int, str]:
    return {h.id: h.name for h in db.execute(select(Hotel)).scalars().all()}
