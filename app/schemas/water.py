from datetime import datetime, timedelta, date
from pydantic import BaseModel, field_validator


class WaterLogCreate(BaseModel):
    amount_ml: int
    logged_at: str | None = None

    @field_validator("amount_ml")
    @classmethod
    def validate_amount(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount_ml must be non-zero")
        return value

    @field_validator("logged_at")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        datetime.fromisoformat(value)
        return value


class WaterSummaryEntry(BaseModel):
    date: str
    amount_ml: int


class WaterSummaryResponse(BaseModel):
    range: dict
    entries: list[WaterSummaryEntry]


class DeviceTokenCreate(BaseModel):
    token: str
    platform: str | None = None


class NotificationRequest(BaseModel):
    title: str
    body: str
