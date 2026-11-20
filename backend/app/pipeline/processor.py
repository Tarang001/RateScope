from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.metrics import (
    ALERTS_CREATED,
    DLQ_COUNT,
    EVENTS_INVALID,
    EVENTS_PROCESSED,
    PROCESSING_LATENCY,
)
from app.detection.anomaly import detect_anomaly
from app.detection.parity import SupplierPrice, detect_parity
from app.models.entities import Alert, DlqEvent, ExchangeRate, Hotel, RateEvent, Room, Supplier, SystemMetric
from app.pipeline.normalize import DEFAULT_RATES, to_usd
from app.pipeline.validate import parse_event
from app.schemas.events import SupplierEvent

logger = logging.getLogger(__name__)


def load_fx(db: Session) -> dict[str, float]:
    rows = db.execute(select(ExchangeRate)).scalars().all()
    if not rows:
        return dict(DEFAULT_RATES)
    return {r.currency.upper(): r.rate_to_usd for r in rows}


def send_dlq(db: Session, payload: dict, reason: str, event_id: str = "unknown", retries: int = 0) -> None:
    db.add(DlqEvent(event_id=event_id, payload=payload, reason=reason, retry_count=retries))
    db.flush()
    EVENTS_INVALID.inc()
    count = db.execute(select(DlqEvent)).scalars().all()
    DLQ_COUNT.set(len(count))


def process_payload(db: Session, payload: dict, settings: Settings) -> str:
    start = time.perf_counter()
    event, err = parse_event(payload)
    if err or event is None:
        send_dlq(db, payload if isinstance(payload, dict) else {"raw": str(payload)}, err or "invalid")
        PROCESSING_LATENCY.observe(time.perf_counter() - start)
        return "dlq"

    existing = db.execute(select(RateEvent).where(RateEvent.event_id == event.event_id)).scalar_one_or_none()
    if existing:
        EVENTS_PROCESSED.labels(status="duplicate").inc()
        PROCESSING_LATENCY.observe(time.perf_counter() - start)
        return "duplicate"

    try:
        stored = persist_event(db, event, settings)
    except ValueError as exc:
        send_dlq(db, payload, str(exc), event.event_id)
        PROCESSING_LATENCY.observe(time.perf_counter() - start)
        return "dlq"

    run_detections(db, stored, settings)
    EVENTS_PROCESSED.labels(status="ok").inc()
    elapsed = time.perf_counter() - start
    PROCESSING_LATENCY.observe(elapsed)
    try:
        record_metric(db, "processing_latency_ms", elapsed * 1000)
    except Exception:
        pass
    return "ok"


def persist_event(db: Session, event: SupplierEvent, settings: Settings) -> RateEvent:
    hotel = db.get(Hotel, event.hotel_id)
    room = db.get(Room, event.room_id)
    supplier = db.execute(select(Supplier).where(Supplier.code == event.supplier_code)).scalar_one_or_none()
    if not hotel or not room or not supplier:
        raise ValueError("unknown_hotel_room_or_supplier")
    if room.hotel_id != hotel.id:
        raise ValueError("room_hotel_mismatch")

    fx = load_fx(db)
    price_usd = to_usd(event.price, event.currency, fx)
    received = event.event_time or datetime.now(timezone.utc).replace(tzinfo=None)

    row = RateEvent(
        event_id=event.event_id,
        hotel_id=hotel.id,
        room_id=room.id,
        supplier_id=supplier.id,
        city=hotel.city,
        stay_date=event.stay_date,
        nights=event.nights,
        currency=event.currency,
        price_original=event.price,
        price_usd=price_usd,
        availability=event.availability,
        occupancy=event.occupancy,
        cancellation_policy=event.cancellation_policy,
        scenario=event.scenario.value,
        received_at=received,
    )
    db.add(row)
    db.flush()
    return row


def fingerprint(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def cooldown_active(db: Session, fp: str, minutes: int) -> bool:
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    row = db.execute(
        select(Alert).where(Alert.fingerprint == fp, Alert.created_at >= cutoff).order_by(Alert.created_at.desc())
    ).scalars().first()
    return row is not None


def run_detections(db: Session, event: RateEvent, settings: Settings) -> None:
    supplier_map = {s.id: s.code for s in db.execute(select(Supplier)).scalars().all()}
    latest_by_supplier: dict[int, RateEvent] = {}
    rows = db.execute(
        select(RateEvent)
        .where(
            RateEvent.hotel_id == event.hotel_id,
            RateEvent.room_id == event.room_id,
            RateEvent.stay_date == event.stay_date,
            RateEvent.cancellation_policy == event.cancellation_policy,
        )
        .order_by(RateEvent.received_at.desc())
        .limit(200)
    ).scalars().all()
    for r in rows:
        if r.supplier_id not in latest_by_supplier:
            latest_by_supplier[r.supplier_id] = r

    prices = [
        SupplierPrice(supplier_code=supplier_map[sid], price_usd=ev.price_usd)
        for sid, ev in latest_by_supplier.items()
        if sid in supplier_map
    ]
    hotel = db.get(Hotel, event.hotel_id)
    city = hotel.city if hotel else event.city
    hotel_name = hotel.name if hotel else f"Hotel {event.hotel_id}"

    parity = detect_parity(
        prices,
        threshold_pct=settings.parity_threshold_pct,
        medium_pct=settings.parity_medium_pct,
        high_pct=settings.parity_high_pct,
    )
    fp_parity = fingerprint("PARITY", event.hotel_id, event.room_id, event.stay_date, event.cancellation_policy)
    open_parity = db.execute(
        select(Alert).where(
            Alert.fingerprint == fp_parity,
            Alert.status.in_(["OPEN", "ACKNOWLEDGED"]),
            Alert.alert_type == "PARITY",
        )
    ).scalars().first()

    if parity and parity.violated:
        if not cooldown_active(db, fp_parity, settings.alert_cooldown_minutes) and not open_parity:
            now = datetime.utcnow()
            alert = Alert(
                alert_type="PARITY",
                severity=parity.severity or "LOW",
                status="OPEN",
                fingerprint=fp_parity,
                hotel_id=event.hotel_id,
                room_id=event.room_id,
                stay_date=event.stay_date,
                city=city,
                supplier_codes=[p.supplier_code for p in prices],
                title=f"Parity break at {hotel_name}: {parity.spread_pct}% spread",
                created_at=now,
                updated_at=now,
                details={
                    "spread_pct": parity.spread_pct,
                    "cheapest": parity.cheapest,
                    "most_expensive": parity.most_expensive,
                    "cheapest_price": parity.cheapest_price,
                    "most_expensive_price": parity.most_expensive_price,
                    "pairs": parity.pairs,
                },
            )
            db.add(alert)
            db.flush()
            ALERTS_CREATED.labels(type="PARITY", severity=alert.severity).inc()
    elif open_parity:
        open_parity.status = "RESOLVED"
        open_parity.resolved_at = datetime.utcnow()
        open_parity.details = {**(open_parity.details or {}), "auto_resolved": True, "last_spread_pct": parity.spread_pct if parity else 0}

    history_rows = db.execute(
        select(RateEvent)
        .where(RateEvent.room_id == event.room_id, RateEvent.supplier_id == event.supplier_id)
        .order_by(RateEvent.received_at.desc())
        .limit(settings.anomaly_window + 5)
    ).scalars().all()
    history_prices = [
        r.price_usd
        for r in reversed([row for row in history_rows if row.event_id != event.event_id][: settings.anomaly_window])
    ]
    anomaly = detect_anomaly(history_prices, event.price_usd, z_threshold=settings.anomaly_zscore)
    if anomaly.triggered:
        fp_anom = fingerprint("ANOMALY", event.hotel_id, event.room_id, event.supplier_id, anomaly.classification)
        if not cooldown_active(db, fp_anom, settings.alert_cooldown_minutes):
            severity = "HIGH" if abs(anomaly.zscore) >= settings.anomaly_zscore + 1 else "MEDIUM"
            code = supplier_map.get(event.supplier_id, "?")
            now = datetime.utcnow()
            alert = Alert(
                alert_type="ANOMALY",
                severity=severity,
                status="OPEN",
                fingerprint=fp_anom,
                hotel_id=event.hotel_id,
                room_id=event.room_id,
                stay_date=event.stay_date,
                city=city,
                supplier_codes=[code],
                title=f"{anomaly.classification} on {hotel_name} via {code} (z={anomaly.zscore})",
                created_at=now,
                updated_at=now,
                details={
                    "classification": anomaly.classification,
                    "zscore": anomaly.zscore,
                    "mean": anomaly.mean,
                    "std": anomaly.std,
                    "price_usd": event.price_usd,
                },
            )
            db.add(alert)
            db.flush()
            ALERTS_CREATED.labels(type="ANOMALY", severity=severity).inc()


def record_metric(db: Session, name: str, value: float) -> None:
    row = db.execute(select(SystemMetric).where(SystemMetric.name == name)).scalar_one_or_none()
    if row is None:
        db.add(SystemMetric(name=name, value=value, extra={}))
    else:
        row.value = value
    db.flush()
