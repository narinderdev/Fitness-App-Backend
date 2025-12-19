from datetime import datetime, date, timedelta

from pydantic import BaseModel, field_validator


class WeightLogCreate(BaseModel):
    weight_kg: float
    logged_at: str | None = None

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("weight must be positive")
        return value

    @field_validator("logged_at")
    @classmethod
    def validate_timestamp(cls, value: str | None) -> str | None:
        if value is None:
            return None
        datetime.fromisoformat(value)
        return value


class WeightLogEntry(BaseModel):
    date: str
    weight_kg: float
    logged_at: str | None = None


class WeightHistoryResponse(BaseModel):
    range: dict
    entries: list[WeightLogEntry]


class WeightLogResponse(BaseModel):
    weight_kg: float
    logged_at: str
