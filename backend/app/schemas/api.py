from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HotelOut(BaseModel):
    id: int
    name: str
    city: str
    country: str
    star_rating: int

    model_config = {"from_attributes": True}


class RoomOut(BaseModel):
    id: int
    hotel_id: int
    room_type: str
    cancellation_policy: str
    occupancy: int

    model_config = {"from_attributes": True}


class SupplierOut(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class HotelRatesOut(BaseModel):
    hotel: HotelOut
    rooms: list[RoomOut]
    latest_rates: list[dict[str, Any]]


class PricePoint(BaseModel):
    received_at: datetime
    stay_date: date
    supplier_code: str
    price_usd: float
    availability: int
    scenario: str


class AlertOut(BaseModel):
    id: int
    alert_type: str
    severity: str
    status: str
    hotel_id: int
    room_id: int
    stay_date: date
    city: str
    supplier_codes: list[str]
    title: str
    details: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    hotel_name: str | None = None

    model_config = {"from_attributes": True}


class AlertPatch(BaseModel):
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]


class ParityPair(BaseModel):
    supplier_a: str
    supplier_b: str
    spread_pct: float
    cheaper: str
    hotel_id: int
    city: str
    stay_date: date
    price_a: float
    price_b: float


class ParityReport(BaseModel):
    generated_at: datetime
    threshold_pct: float
    pairs: list[ParityPair]
    city_heatmap: list[dict[str, Any]]
    open_alerts: int


class DailyStatOut(BaseModel):
    stat_date: date
    hotel_id: int
    city: str
    avg_price: float
    median_price: float
    volatility: float
    parity_violations: int
    demand_score: float
    event_count: int
    hotel_name: str | None = None

    model_config = {"from_attributes": True}


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    question: str
    llm_enabled: bool
    filters: dict[str, Any]
    explanation: str
    results: dict[str, Any]
    fallback: bool = False


class HealthDetail(BaseModel):
    status: str
    postgres: bool
    redis: bool
    kafka: bool
    events_processed: int
    dlq_count: int
    consumer_lag: float
    processing_latency_ms: float
