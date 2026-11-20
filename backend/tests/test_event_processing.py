from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.models.entities import Alert, DlqEvent, Hotel, RateEvent, Room, Supplier
from app.pipeline.processor import process_payload


def _payload(hotel, room, supplier, event_id, price=100.0, scenario="NORMAL"):
    return {
        "event_id": event_id,
        "hotel_id": hotel.id,
        "room_id": room.id,
        "supplier_code": supplier.code,
        "stay_date": date.today().isoformat(),
        "currency": "USD",
        "price": price,
        "availability": 10,
        "cancellation_policy": room.cancellation_policy,
        "scenario": scenario,
        "event_time": datetime.utcnow().isoformat(),
    }


def test_stores_valid_and_dedupes(db):
    settings = get_settings()
    hotel = db.query(Hotel).first()
    room = db.query(Room).filter(Room.hotel_id == hotel.id).first()
    supplier = db.query(Supplier).first()
    p = _payload(hotel, room, supplier, "evt-unique-0001")
    assert process_payload(db, p, settings) == "ok"
    assert process_payload(db, p, settings) == "duplicate"
    count = db.execute(select(RateEvent)).scalars().all()
    assert len(count) == 1


def test_malformed_goes_to_dlq(db):
    settings = get_settings()
    assert process_payload(db, {"bad": True}, settings) == "dlq"
    assert db.execute(select(DlqEvent)).scalars().first() is not None


def test_parity_alert_and_auto_resolve(db):
    settings = get_settings()
    hotel = db.query(Hotel).first()
    room = db.query(Room).filter(Room.hotel_id == hotel.id).first()
    suppliers = db.query(Supplier).order_by(Supplier.id).all()
    process_payload(db, _payload(hotel, room, suppliers[0], "parity-p1", price=100), settings)
    process_payload(db, _payload(hotel, room, suppliers[1], "parity-p2", price=130), settings)
    alerts = db.execute(select(Alert).where(Alert.alert_type == "PARITY")).scalars().all()
    assert alerts
    process_payload(db, _payload(hotel, room, suppliers[1], "parity-p3", price=102), settings)
    db.refresh(alerts[0])
    assert alerts[0].status == "RESOLVED"


def test_anomaly_cooldown(db):
    settings = get_settings()
    hotel = db.query(Hotel).first()
    room = db.query(Room).filter(Room.hotel_id == hotel.id).first()
    supplier = db.query(Supplier).first()
    base_time = datetime.utcnow() - timedelta(hours=5)
    for i in range(12):
        payload = _payload(hotel, room, supplier, f"hist-{i:04d}", price=100 + i * 0.3)
        payload["event_time"] = (base_time + timedelta(minutes=i * 10)).isoformat()
        process_payload(db, payload, settings)
    process_payload(db, _payload(hotel, room, supplier, "spike-001", price=400), settings)
    process_payload(db, _payload(hotel, room, supplier, "spike-002", price=410), settings)
    anomalies = db.execute(select(Alert).where(Alert.alert_type == "ANOMALY")).scalars().all()
    assert len(anomalies) == 1
