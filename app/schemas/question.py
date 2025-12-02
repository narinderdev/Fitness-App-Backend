from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AnswerTypeEnum(str, Enum):
    single_choice = "single_choice"
    multi_choice = "multi_choice"
    text = "text"
    number = "number"
    date = "date"
    weight = "weight"
    height = "height"
    other = "other"


class AnswerOptionBase(BaseModel):
    option_text: str
    value: str | None = None
    is_active: bool = True


class AnswerOptionCreate(AnswerOptionBase):
    pass


class AnswerOptionUpdate(BaseModel):
    id: int | None = None
    option_text: str
    value: str | None = None
    is_active: bool | None = None


class AnswerOptionResponse(AnswerOptionBase):
    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionBase(BaseModel):
    question: str
    description: str | None = None
    answer_type: AnswerTypeEnum
    gender: str | None = None
    is_required: bool = False
    is_active: bool = True


class QuestionCreate(QuestionBase):
    options: list[AnswerOptionCreate] | None = None


class QuestionUpdate(BaseModel):
    question: str | None = None
    description: str | None = None
    answer_type: AnswerTypeEnum | None = None
    gender: str | None = None
    is_required: bool | None = None
    is_active: bool | None = None
    options: list[AnswerOptionUpdate] | None = None


class QuestionResponse(BaseModel):
    id: int
    question: str
    description: str | None
    answer_type: AnswerTypeEnum
    gender: str | None
    is_required: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    options: list[AnswerOptionResponse]

    model_config = {"from_attributes": True}
