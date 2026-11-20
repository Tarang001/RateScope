from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Scenario(str, Enum):
    NORMAL = "NORMAL"
    PRICE_SPIKE = "PRICE_SPIKE"
    PRICE_DROP = "PRICE_DROP"
    PARITY_BREAK = "PARITY_BREAK"
    DUPLICATES = "DUPLICATES"
    MALFORMED = "MALFORMED"
    BURST = "BURST"


class SupplierEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    hotel_id: int
    room_id: int
    supplier_code: str = Field(min_length=2, max_length=32)
    stay_date: date
    nights: int = Field(ge=1, le=30, default=1)
    currency: str = Field(min_length=3, max_length=8)
    price: float = Field(gt=0, le=100000)
    availability: int = Field(ge=0, le=500)
    occupancy: int = Field(ge=1, le=8, default=2)
    cancellation_policy: str
    scenario: Scenario = Scenario.NORMAL
    event_time: datetime | None = None

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("supplier_code")
    @classmethod
    def supplier_upper(cls, v: str) -> str:
        return v.upper()


class RateEventOut(BaseModel):
    id: int
    event_id: str
    hotel_id: int
    room_id: int
    supplier_id: int
    city: str
    stay_date: date
    currency: str
    price_original: float
    price_usd: float
    availability: int
    cancellation_policy: str
    scenario: str
    received_at: datetime

    model_config = {"from_attributes": True}
