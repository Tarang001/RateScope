from datetime import date, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.models.entities import DlqEvent, Hotel, RateEvent, Room, Supplier
from app.pipeline.processor import process_payload


def test_full_ingest_normalize_and_dlq(db):
    settings = get_settings()
    hotel = db.execute(select(Hotel)).scalars().first()
    room = db.execute(select(Room).where(Room.hotel_id == hotel.id)).scalars().first()
    supplier = db.execute(select(Supplier).where(Supplier.code == "AGODA")).scalars().first()
    payload = {
        "event_id": "int-fx-0001",
        "hotel_id": hotel.id,
        "room_id": room.id,
        "supplier_code": "AGODA",
        "stay_date": date.today().isoformat(),
        "currency": "INR",
        "price": 10000,
        "availability": 9,
        "cancellation_policy": room.cancellation_policy,
        "event_time": datetime.utcnow().isoformat(),
    }
    assert process_payload(db, payload, settings) == "ok"
    stored = db.execute(select(RateEvent).where(RateEvent.event_id == "int-fx-0001")).scalar_one()
    assert stored.price_usd == 120.0
    assert process_payload(db, {"event_id": "x", "price": -1}, settings) == "dlq"
    assert db.execute(select(DlqEvent)).scalars().first() is not None
