from app.core.config import get_settings
from app.llm.ask import AskFilters, heuristic_filters
from app.models.entities import Hotel, Room, Supplier
from app.pipeline.processor import process_payload


def test_health_live(client):
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_hotels_requires_key(client):
    assert client.get("/api/v1/hotels").status_code == 401
    resp = client.get("/api/v1/hotels", headers={"X-API-Key": "ratescope-demo-key"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 12


def test_alerts_ack_resolve(client, db):
    settings = get_settings()
    hotel = db.query(Hotel).first()
    room = db.query(Room).filter(Room.hotel_id == hotel.id).first()
    suppliers = db.query(Supplier).all()
    from datetime import date, datetime

    def payload(sup, eid, price):
        return {
            "event_id": eid,
            "hotel_id": hotel.id,
            "room_id": room.id,
            "supplier_code": sup.code,
            "stay_date": date.today().isoformat(),
            "currency": "USD",
            "price": price,
            "availability": 4,
            "cancellation_policy": room.cancellation_policy,
            "event_time": datetime.utcnow().isoformat(),
        }

    process_payload(db, payload(suppliers[0], "alert-a1", 100), settings)
    process_payload(db, payload(suppliers[1], "alert-a2", 140), settings)
    db.commit()
    headers = {"X-API-Key": "ratescope-demo-key"}
    listed = client.get("/api/v1/alerts", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items
    alert_id = items[0]["id"]
    patched = client.patch(f"/api/v1/alerts/{alert_id}", headers=headers, json={"status": "ACKNOWLEDGED"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "ACKNOWLEDGED"


def test_ask_fallback_filters():
    f = heuristic_filters("Which suppliers have the highest price differences in Delhi?")
    assert f.city == "Delhi"
    assert f.intent in {"parity", "alerts", "compare_suppliers"}
    AskFilters.model_validate(f.model_dump())


def test_ask_endpoint_without_llm(client):
    resp = client.post(
        "/api/v1/ask",
        headers={"X-API-Key": "ratescope-demo-key"},
        json={"question": "Show high-severity alerts from the last seven days"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["fallback"] is True
    assert body["filters"]["severity"] == "HIGH"
