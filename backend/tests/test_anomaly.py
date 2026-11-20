from app.detection.anomaly import detect_anomaly, moving_average


def test_spike_detected():
    history = [100.0] * 20
    result = detect_anomaly(history, 160.0, z_threshold=2.5, min_points=8)
    # zero std -> not triggered
    assert result.triggered is False

    history = [100 + i * 0.2 for i in range(20)]
    result = detect_anomaly(history, 180.0, z_threshold=2.5, min_points=8)
    assert result.triggered
    assert result.classification == "SPIKE"


def test_drop_detected():
    history = [120 - i * 0.1 for i in range(20)]
    result = detect_anomaly(history, 40.0, z_threshold=2.5)
    assert result.triggered
    assert result.classification == "DROP"


def test_insufficient_history():
    result = detect_anomaly([100.0, 101.0], 200.0, min_points=8)
    assert result.triggered is False


def test_moving_average():
    assert moving_average([10, 20, 30], 2) == 25
    assert moving_average([], 3) is None
