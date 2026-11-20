from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import ExchangeRate, Hotel, RateEvent, Room, Supplier
from app.pipeline.processor import process_payload
from app.simulator.engine import build_event, catalog

CITIES = [
    ("The Imperial Delhi", "Delhi", "India", 5),
    ("Lotus Park Inn", "Delhi", "India", 4),
    ("Yamuna Business Hotel", "Delhi", "India", 3),
    ("Siam Riverside", "Bangkok", "Thailand", 5),
    ("Sukhumvit Grid", "Bangkok", "Thailand", 4),
    ("Marina Bay Ledger", "Singapore", "Singapore", 5),
    ("Orchard Transit Hotel", "Singapore", "Singapore", 4),
    ("Shibuya Lantern", "Tokyo", "Japan", 4),
    ("Ginza Current", "Tokyo", "Japan", 5),
    ("Creek Palace Dubai", "Dubai", "UAE", 5),
    ("Deira Trade Hotel", "Dubai", "UAE", 3),
    ("Hudson Point NYC", "New York", "USA", 4),
]

ROOM_TYPES = [
    ("STANDARD", "NON_REFUNDABLE", 2),
    ("DELUXE", "FREE_24H", 2),
    ("SUITE", "FLEXIBLE", 3),
]

SUPPLIERS = [
    ("AGODA", "Agoda", 0.0),
    ("BOOKING", "Booking.com", 3.5),
    ("EXPEDIA", "Expedia", 4.2),
]

FX = {
    "USD": 1.0,
    "INR": 0.012,
    "THB": 0.029,
    "SGD": 0.74,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "AED": 0.27,
}


def seed_reference(db: Session) -> None:
    if db.execute(select(Supplier)).scalars().first():
        return
    for code, name, markup in SUPPLIERS:
        db.add(Supplier(code=code, name=name, markup_pct=markup))
    for cur, rate in FX.items():
        db.add(ExchangeRate(currency=cur, rate_to_usd=rate))
    db.flush()
    for name, city, country, stars in CITIES:
        hotel = Hotel(name=name, city=city, country=country, star_rating=stars)
        db.add(hotel)
        db.flush()
        for room_type, policy, occ in ROOM_TYPES:
            db.add(Room(hotel_id=hotel.id, room_type=room_type, cancellation_policy=policy, occupancy=occ))
    db.flush()


def seed_history(db: Session, days: int = 10, per_day: int = 8) -> int:
    settings = get_settings()
    if db.execute(select(RateEvent)).scalars().first():
        return 0
    hotels, rooms, suppliers = catalog(db)
    if not hotels:
        return 0
    count = 0
    today = date.today()
    for d in range(days, 0, -1):
        stay = today + timedelta(days=(d % 14))
        received = datetime.utcnow() - timedelta(days=d)
        for i in range(per_day):
            hotel = hotels[(d + i) % len(hotels)]
            room_opts = rooms[hotel.id]
            room = room_opts[i % len(room_opts)]
            supplier = suppliers[i % len(suppliers)]
            scenario = "NORMAL"
            if i % 11 == 0:
                scenario = "PARITY_BREAK"
            elif i % 13 == 0:
                scenario = "PRICE_SPIKE"
            elif i % 17 == 0:
                scenario = "PRICE_DROP"
            payload = build_event(hotel, room, supplier, stay, received, scenario, seed=d * 100 + i)
            process_payload(db, payload, settings)
            count += 1
    # Same hotel/room/stay across suppliers so parity and anomaly detectors fire immediately.
    hotel = hotels[0]
    room = rooms[hotel.id][0]
    stay = today + timedelta(days=3)
    received = datetime.utcnow()
    process_payload(db, build_event(hotel, room, suppliers[0], stay, received, "NORMAL", seed=9001), settings)
    process_payload(db, build_event(hotel, room, suppliers[1], stay, received, "PARITY_BREAK", seed=9002), settings)
    process_payload(db, build_event(hotel, room, suppliers[2], stay, received, "PARITY_BREAK", seed=9003), settings)
    count += 3
    for i in range(12):
        ts = received - timedelta(minutes=40 - i)
        process_payload(
            db,
            build_event(hotel, room, suppliers[0], stay, ts, "NORMAL", seed=9100 + i),
            settings,
        )
        count += 1
    spike = build_event(hotel, room, suppliers[0], stay, received + timedelta(seconds=1), "PRICE_SPIKE", seed=9200)
    process_payload(db, spike, settings)
    count += 1
    db.flush()
    return count
