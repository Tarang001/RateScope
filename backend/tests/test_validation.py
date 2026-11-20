from app.pipeline.normalize import to_usd
from app.pipeline.validate import parse_event


def test_valid_event():
    event, err = parse_event(
        {
            "event_id": "evt-12345678",
            "hotel_id": 1,
            "room_id": 1,
            "supplier_code": "agoda",
            "stay_date": "2026-11-21",
            "currency": "inr",
            "price": 8500,
            "availability": 12,
            "cancellation_policy": "FREE_24H",
        }
    )
    assert err is None
    assert event is not None
    assert event.supplier_code == "AGODA"
    assert event.currency == "INR"


def test_malformed_event():
    event, err = parse_event({"price": "nope"})
    assert event is None
    assert err and err.startswith("validation_error")


def test_currency_normalization():
    assert to_usd(100, "USD") == 100
    assert round(to_usd(100, "INR"), 2) == 1.2


def test_unknown_currency():
    try:
        to_usd(10, "XYZ")
        assert False
    except ValueError as exc:
        assert "Unsupported" in str(exc)
