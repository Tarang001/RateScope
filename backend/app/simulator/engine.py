from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Hotel, Room, Supplier

CITY_CURRENCY = {
    "Delhi": "INR",
    "Bangkok": "THB",
    "Singapore": "SGD",
    "Tokyo": "JPY",
    "Dubai": "AED",
    "New York": "USD",
}

BASE_USD = {
    "STANDARD": 95,
    "DELUXE": 145,
    "SUITE": 240,
}

CITY_MULT = {
    "Delhi": 0.72,
    "Bangkok": 0.8,
    "Singapore": 1.25,
    "Tokyo": 1.18,
    "Dubai": 1.35,
    "New York": 1.7,
}


def catalog(db: Session) -> tuple[list[Hotel], dict[int, list[Room]], list[Supplier]]:
    hotels = list(db.execute(select(Hotel).order_by(Hotel.id)).scalars().all())
    rooms = list(db.execute(select(Room).order_by(Room.id)).scalars().all())
    suppliers = list(db.execute(select(Supplier).order_by(Supplier.id)).scalars().all())
    by_hotel: dict[int, list[Room]] = {}
    for r in rooms:
        by_hotel.setdefault(r.hotel_id, []).append(r)
    return hotels, by_hotel, suppliers


def _event_id(parts: str) -> str:
    return hashlib.sha1(parts.encode()).hexdigest()[:16]


def price_for(
    hotel: Hotel,
    room: Room,
    supplier: Supplier,
    stay: date,
    received: datetime,
    scenario: str,
    rng: random.Random,
) -> tuple[float, str]:
    base = BASE_USD.get(room.room_type, 100) * CITY_MULT.get(hotel.city, 1.0)
    weekend = stay.weekday() >= 5
    if weekend:
        base *= 1.18
    month = stay.month
    if month in {12, 1, 7, 8}:
        base *= 1.22
    elif month in {4, 5}:
        base *= 0.92
    hour = received.hour
    if 18 <= hour <= 22:
        base *= 1.08
    base *= 1 + supplier.markup_pct / 100
    noise = rng.uniform(-0.04, 0.05)
    base *= 1 + noise
    if scenario == "PRICE_SPIKE":
        base *= rng.uniform(1.45, 1.9)
    elif scenario == "PRICE_DROP":
        base *= rng.uniform(0.45, 0.7)
    elif scenario == "PARITY_BREAK" and supplier.code != "AGODA":
        base *= rng.uniform(1.2, 1.45)
    currency = CITY_CURRENCY.get(hotel.city, "USD")
    # convert USD estimate back to local currency using inverse of seed FX
    inv = {
        "USD": 1.0,
        "INR": 1 / 0.012,
        "THB": 1 / 0.029,
        "SGD": 1 / 0.74,
        "JPY": 1 / 0.0067,
        "AED": 1 / 0.27,
    }
    local = round(base * inv.get(currency, 1.0), 2)
    return local, currency


def build_event(
    hotel: Hotel,
    room: Room,
    supplier: Supplier,
    stay: date,
    received: datetime,
    scenario: str,
    seed: int,
    duplicate_of: str | None = None,
) -> dict:
    rng = random.Random(seed)
    if scenario == "MALFORMED":
        return {"event_id": "bad", "price": "free", "hotel_id": hotel.id}
    price, currency = price_for(hotel, room, supplier, stay, received, scenario, rng)
    eid = duplicate_of or _event_id(f"{hotel.id}|{room.id}|{supplier.code}|{stay}|{received.isoformat()}|{seed}")
    avail = max(0, int(40 - (12 if stay.weekday() >= 5 else 0) + rng.randint(-8, 10)))
    return {
        "event_id": eid,
        "hotel_id": hotel.id,
        "room_id": room.id,
        "supplier_code": supplier.code,
        "stay_date": stay.isoformat(),
        "nights": 1,
        "currency": currency,
        "price": price,
        "availability": avail,
        "occupancy": room.occupancy,
        "cancellation_policy": room.cancellation_policy,
        "scenario": scenario if scenario != "DUPLICATES" else "NORMAL",
        "event_time": received.isoformat(),
    }


def next_batch(db: Session, tick: int, burst: bool = False) -> list[dict]:
    hotels, rooms, suppliers = catalog(db)
    if not hotels:
        return []
    n = 12 if burst else 3
    events = []
    now = datetime.utcnow()
    for i in range(n):
        hotel = hotels[(tick + i) % len(hotels)]
        room = rooms[hotel.id][(tick + i) % len(rooms[hotel.id])]
        supplier = suppliers[(tick + i) % len(suppliers)]
        stay = date.today() + timedelta(days=(tick + i) % 21)
        scenario = "NORMAL"
        roll = (tick + i) % 40
        if roll == 3:
            scenario = "PRICE_SPIKE"
        elif roll == 7:
            scenario = "PRICE_DROP"
        elif roll == 11:
            scenario = "PARITY_BREAK"
        elif roll == 17:
            scenario = "MALFORMED"
        elif roll == 23:
            scenario = "DUPLICATES"
        elif roll == 29:
            scenario = "BURST"
        payload = build_event(hotel, room, supplier, stay, now, scenario, seed=tick * 50 + i)
        events.append(payload)
        if scenario == "DUPLICATES":
            events.append(dict(payload))
        if scenario == "BURST":
            for extra in range(4):
                s2 = suppliers[extra % len(suppliers)]
                events.append(build_event(hotel, room, s2, stay, now, "NORMAL", seed=tick * 50 + i + extra + 10))
    return events
