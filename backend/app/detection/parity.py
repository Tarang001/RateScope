from dataclasses import dataclass


SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"


@dataclass
class SupplierPrice:
    supplier_code: str
    price_usd: float


@dataclass
class ParityResult:
    spread_pct: float
    cheapest: str
    most_expensive: str
    cheapest_price: float
    most_expensive_price: float
    severity: str | None
    violated: bool
    pairs: list[dict]


def classify_severity(spread_pct: float, medium: float, high: float, threshold: float) -> str | None:
    if spread_pct < threshold:
        return None
    if spread_pct >= high:
        return SEVERITY_HIGH
    if spread_pct >= medium:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def detect_parity(
    prices: list[SupplierPrice],
    threshold_pct: float = 8.0,
    medium_pct: float = 12.0,
    high_pct: float = 20.0,
) -> ParityResult | None:
    unique: dict[str, float] = {}
    for p in prices:
        if p.price_usd <= 0:
            continue
        unique[p.supplier_code] = p.price_usd
    if len(unique) < 2:
        return None

    cheapest_code = min(unique, key=unique.get)
    expensive_code = max(unique, key=unique.get)
    cheap = unique[cheapest_code]
    expensive = unique[expensive_code]
    spread = ((expensive - cheap) / cheap) * 100 if cheap else 0.0
    severity = classify_severity(spread, medium_pct, high_pct, threshold_pct)

    pairs = []
    codes = sorted(unique.keys())
    for i, a in enumerate(codes):
        for b in codes[i + 1 :]:
            pa, pb = unique[a], unique[b]
            low = min(pa, pb)
            high = max(pa, pb)
            pair_spread = ((high - low) / low) * 100 if low else 0.0
            pairs.append(
                {
                    "supplier_a": a,
                    "supplier_b": b,
                    "price_a": round(pa, 2),
                    "price_b": round(pb, 2),
                    "spread_pct": round(pair_spread, 2),
                    "cheaper": a if pa <= pb else b,
                }
            )

    return ParityResult(
        spread_pct=round(spread, 2),
        cheapest=cheapest_code,
        most_expensive=expensive_code,
        cheapest_price=round(cheap, 2),
        most_expensive_price=round(expensive, 2),
        severity=severity,
        violated=severity is not None,
        pairs=pairs,
    )
