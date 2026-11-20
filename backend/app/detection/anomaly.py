from dataclasses import dataclass

import numpy as np


@dataclass
class AnomalyResult:
    zscore: float
    mean: float
    std: float
    classification: str | None
    triggered: bool


def detect_anomaly(
    history: list[float],
    current: float,
    z_threshold: float = 2.5,
    min_points: int = 8,
) -> AnomalyResult:
    if current <= 0 or len(history) < min_points:
        return AnomalyResult(zscore=0.0, mean=0.0, std=0.0, classification=None, triggered=False)

    arr = np.array(history, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    if std < 1e-6:
        return AnomalyResult(zscore=0.0, mean=mean, std=std, classification=None, triggered=False)

    z = (current - mean) / std
    classification = None
    if z >= z_threshold:
        classification = "SPIKE"
    elif z <= -z_threshold:
        classification = "DROP"
    return AnomalyResult(
        zscore=round(float(z), 3),
        mean=round(mean, 2),
        std=round(std, 2),
        classification=classification,
        triggered=classification is not None,
    )


def moving_average(values: list[float], window: int) -> float | None:
    if not values or window <= 0:
        return None
    slice_ = values[-window:]
    return float(np.mean(slice_))
