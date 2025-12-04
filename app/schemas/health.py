from datetime import date
from pydantic import BaseModel, field_validator


class StepCreate(BaseModel):
    date: str
    steps: int
    source: str

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, value: int) -> int:
        if value < 0:
            raise ValueError("steps must be non-negative")
        return value


class StepResponse(BaseModel):
    date: str
    steps: int
    source: str | None = None

    model_config = {"from_attributes": True}
