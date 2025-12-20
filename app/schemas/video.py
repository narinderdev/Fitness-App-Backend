from enum import Enum
from datetime import datetime
from pydantic import BaseModel, AnyHttpUrl, field_validator


class GenderEnum(str, Enum):
    male = "Male"
    female = "Female"
    both = "Both"
    all = "All"


class BodyPartEnum(str, Enum):
    core = "Core"
    arms = "Arms"
    full_body = "FullBody"
    legs = "Legs"
    full_body_strength = "FullBodyStrength"
    sport_nutrition = "SportNutrition"


class VideoCreateRequest(BaseModel):
    body_part: str | None = None
    gender: str | None = None
    title: str | None = None
    description: str | None = None
    video_url: AnyHttpUrl
    thumbnail_url: AnyHttpUrl

    @field_validator("body_part")
    @classmethod
    def validate_body_part(cls, value: str | None) -> str:
        if value in (None, ""):
            return ""
        allowed = {item.value for item in BodyPartEnum}
        if value not in allowed:
            raise ValueError("Input should be 'Core', 'Arms', 'FullBody', 'Legs', 'FullBodyStrength' or 'SportNutrition'")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str | None) -> str:
        if value in (None, ""):
            return ""
        allowed = {item.value for item in GenderEnum}
        if value not in allowed:
            raise ValueError("Input should be 'Male', 'Female', 'Both' or 'All'")
        return value


class VideoUpdateRequest(BaseModel):
    body_part: str | None = None
    gender: str | None = None
    title: str | None = None
    description: str | None = None
    video_url: AnyHttpUrl | None = None
    thumbnail_url: AnyHttpUrl | None = None

    @field_validator("body_part")
    @classmethod
    def validate_body_part(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return "" if value == "" else None
        allowed = {item.value for item in BodyPartEnum}
        if value not in allowed:
            raise ValueError("Input should be 'Core', 'Arms', 'FullBody', 'Legs', 'FullBodyStrength' or 'SportNutrition'")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return "" if value == "" else None
        allowed = {item.value for item in GenderEnum}
        if value not in allowed:
            raise ValueError("Input should be 'Male', 'Female', 'Both' or 'All'")
        return value


class VideoResponse(BaseModel):
    id: int
    title: str | None = None
    description: str | None = None
    body_part: str
    gender: str
    video_url: str
    thumbnail_url: str
    created_at: datetime

    model_config = {"from_attributes": True}
