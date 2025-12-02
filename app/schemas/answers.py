from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import List, Optional


class UserAnswerOptionCreate(BaseModel):
    option_id: int


class UserAnswerCreate(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    options: Optional[List[UserAnswerOptionCreate]] = None

    @field_validator("options")
    def validate_options(cls, value):
        if value is not None and not isinstance(value, list):
            raise ValueError("options must be a list if provided")
        return value


class UserAnswerOptionResponse(BaseModel):
    id: int
    option_id: int
    option_text: str
    value: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAnswerResponse(BaseModel):
    id: int
    question_id: int
    answer_text: str | None
    created_at: datetime
    options: list[UserAnswerOptionResponse] | None

    model_config = {"from_attributes": True}
