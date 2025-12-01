from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ValidationInfo, field_validator


class QuestionTypeEnum(str, Enum):
    weight = "weight"
    height = "height"
    habits = "habits"
    nutrition = "nutrition"
    other = "other"


class QuestionBase(BaseModel):
    prompt: str
    answer: str
    gender: str | None = None
    question_type: QuestionTypeEnum
    measurement_units: list[str] | None = None

    @field_validator("measurement_units")
    @classmethod
    def validate_measurement_units(cls, value, info: ValidationInfo):
        if value is not None:
            cleaned = [unit.strip() for unit in value if isinstance(unit, str) and unit.strip()]
            value = cleaned or None

        question_type = info.data.get("question_type")
        if question_type in {QuestionTypeEnum.weight, QuestionTypeEnum.height} and not value:
            raise ValueError("measurement_units is required for weight or height questions")
        return value


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    prompt: str | None = None
    answer: str | None = None
    gender: str | None = None
    question_type: QuestionTypeEnum | None = None
    measurement_units: list[str] | None = None


class QuestionResponse(BaseModel):
    id: int
    prompt: str
    answer: str
    gender: str | None
    question_type: QuestionTypeEnum
    measurement_units: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
