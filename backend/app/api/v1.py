from __future__ import annotations

import asyncio
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.cache import cache_get, cache_set
from app.api.deps import auth
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.metrics import CONSUMER_LAG
from app.core.redis import ping_redis
from app.llm.ask import ask as ask_service
from app.models.entities import Hotel
from app.pipeline.kafka import kafka_ready
from app.repositories import queries
from app.schemas.api import AlertPatch, AskRequest, HotelOut
from app.services.parity_report import build_parity_report

router = APIRouter(prefix="/api/v1")
protected = APIRouter(dependencies=[Depends(auth)])


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    pg = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        pg = False
    redis_ok = ping_redis()
    status = "ok" if pg and redis_ok else "degraded"
    return {"status": status, "checks": {"postgres": pg, "redis": redis_ok}}


@protected.get("/hotels", response_model=list[HotelOut])
def hotels(city: str | None = None, db: Session = Depends(get_db)):
    key = f"hotels:{city or 'all'}"
    cached = cache_get(key)
    if cached:
        return cached
    rows = queries.list_hotels(db, city)
    data = [HotelOut.model_validate(r).model_dump() for r in rows]
    cache_set(key, data, ttl=60)
    return data


@protected.get("/hotels/{hotel_id}/rates")
def hotel_rates(
    hotel_id: int,
    stay_date: date | None = None,
    db: Session = Depends(get_db),
):
    hotel = queries.get_hotel(db, hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    rooms = queries.rooms_for_hotel(db, hotel_id)
    rates = queries.latest_rates_for_hotel(db, hotel_id, stay_date)
    return {
        "hotel": HotelOut.model_validate(hotel).model_dump(),
        "rooms": [
            {
                "id": r.id,
                "hotel_id": r.hotel_id,
                "room_type": r.room_type,
                "cancellation_policy": r.cancellation_policy,
                "occupancy": r.occupancy,
            }
            for r in rooms
        ],
        "latest_rates": rates,
    }


@protected.get("/rooms/{room_id}/price-history")
def price_history(
    room_id: int,
    stay_date: date | None = None,
    supplier: str | None = None,
    db: Session = Depends(get_db),
):
    points = queries.price_history(db, room_id, stay_date, supplier)
    return {"items": points}


@protected.get("/alerts")
def alerts(
    city: str | None = None,
    supplier: str | None = None,
    type: str | None = Query(default=None, alias="type"),
    severity: str | None = None,
    status: str | None = None,
    cursor: int | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows, has_more = queries.list_alerts(db, city, supplier, type, severity, status, cursor, limit)
    names = queries.hotel_name_map(db)
    items = []
    for a in rows:
        items.append(
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "status": a.status,
                "hotel_id": a.hotel_id,
                "room_id": a.room_id,
                "stay_date": a.stay_date.isoformat(),
                "city": a.city,
                "supplier_codes": a.supplier_codes,
                "title": a.title,
                "details": a.details,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "hotel_name": names.get(a.hotel_id),
            }
        )
    next_cursor = items[-1]["id"] if has_more and items else None
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


@protected.patch("/alerts/{alert_id}")
def update_alert(alert_id: int, body: AlertPatch, db: Session = Depends(get_db)):
    alert = queries.patch_alert(db, alert_id, body.status)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"id": alert.id, "status": alert.status}


@protected.get("/parity/report")
def parity_report(city: str | None = None, db: Session = Depends(get_db)):
    settings = get_settings()
    key = f"parity:{city or 'all'}"
    cached = cache_get(key)
    if cached:
        return cached
    data = build_parity_report(db, settings, city)
    cache_set(key, data, ttl=20)
    return data


@protected.get("/stats/daily")
def stats_daily(
    city: str | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    rows = queries.daily_stats(db, city, start, end)
    names = queries.hotel_name_map(db)
    return {
        "items": [
            {
                "stat_date": r.stat_date.isoformat(),
                "hotel_id": r.hotel_id,
                "city": r.city,
                "avg_price": r.avg_price,
                "median_price": r.median_price,
                "volatility": r.volatility,
                "parity_violations": r.parity_violations,
                "demand_score": r.demand_score,
                "event_count": r.event_count,
                "hotel_name": names.get(r.hotel_id),
            }
            for r in rows
        ]
    }


@protected.get("/overview")
def overview(db: Session = Depends(get_db)):
    data = queries.overview(db)
    cache_set("overview", data, ttl=10)
    return data


@protected.get("/health/system")
async def system_health(db: Session = Depends(get_db)):
    counts = queries.system_health_counts(db)
    pg = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        pg = False
    return {
        "status": "ok" if pg else "down",
        "postgres": pg,
        "redis": ping_redis(),
        "kafka": await kafka_ready(),
        "events_processed": counts["events_processed"],
        "dlq_count": counts["dlq_count"],
        "consumer_lag": counts["consumer_lag"] or float(CONSUMER_LAG._value.get() if hasattr(CONSUMER_LAG, "_value") else 0),
        "processing_latency_ms": counts["processing_latency_ms"],
        "api_health": "up",
    }


@protected.post("/ask")
async def ask_endpoint(body: AskRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    return await ask_service(db, body.question, settings)


@protected.get("/stream/alerts")
async def stream_alerts(city: str | None = None):
    async def gen():
        last_id = 0
        from app.core.db import SessionLocal

        while True:
            db = SessionLocal()
            try:
                rows, _ = queries.list_alerts(db, city=city, cursor=None, limit=15)
                names = queries.hotel_name_map(db)
                payload = [
                    {
                        "id": a.id,
                        "alert_type": a.alert_type,
                        "severity": a.severity,
                        "status": a.status,
                        "title": a.title,
                        "city": a.city,
                        "hotel_name": names.get(a.hotel_id),
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in rows
                    if a.id > last_id or True
                ]
                if rows:
                    last_id = max(a.id for a in rows)
                yield f"data: {json.dumps({'items': payload})}\n\n"
            finally:
                db.close()
            await asyncio.sleep(2)

    return StreamingResponse(gen(), media_type="text/event-stream")


@protected.get("/suppliers")
def suppliers(db: Session = Depends(get_db)):
    from app.models.entities import Supplier
    from sqlalchemy import select

    rows = db.execute(select(Supplier).order_by(Supplier.code)).scalars().all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]


router.include_router(protected)
