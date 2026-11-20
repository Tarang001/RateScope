DEFAULT_RATES = {
    "USD": 1.0,
    "INR": 0.012,
    "THB": 0.029,
    "SGD": 0.74,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "AED": 0.27,
}


def to_usd(amount: float, currency: str, table: dict[str, float] | None = None) -> float:
    rates = table or DEFAULT_RATES
    rate = rates.get(currency.upper())
    if rate is None:
        raise ValueError(f"Unsupported currency: {currency}")
    return round(amount * rate, 4)
