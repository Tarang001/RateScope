from app.detection.parity import SupplierPrice, classify_severity, detect_parity


def test_no_parity_when_single_supplier():
    result = detect_parity([SupplierPrice("AGODA", 100)])
    assert result is None


def test_spread_and_cheapest():
    result = detect_parity(
        [
            SupplierPrice("AGODA", 100),
            SupplierPrice("BOOKING", 115),
            SupplierPrice("EXPEDIA", 130),
        ]
    )
    assert result is not None
    assert result.cheapest == "AGODA"
    assert result.most_expensive == "EXPEDIA"
    assert result.spread_pct == 30.0
    assert result.violated
    assert result.severity == "HIGH"
    assert len(result.pairs) == 3


def test_below_threshold_not_violated():
    result = detect_parity(
        [SupplierPrice("AGODA", 100), SupplierPrice("BOOKING", 105)],
        threshold_pct=8,
    )
    assert result is not None
    assert result.violated is False
    assert result.severity is None


def test_severity_buckets():
    assert classify_severity(9, 12, 20, 8) == "LOW"
    assert classify_severity(15, 12, 20, 8) == "MEDIUM"
    assert classify_severity(25, 12, 20, 8) == "HIGH"
    assert classify_severity(2, 12, 20, 8) is None
