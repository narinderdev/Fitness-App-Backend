from enum import Enum
from datetime import datetime
import re
from pydantic import BaseModel, AnyHttpUrl, Field, field_validator


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
    free_workout_1 = "FREE WORKOUT #1"
    free_workout_2 = "FREE WORKOUT #2"


BODY_PART_ALIASES = {
    "core": "Core",
    "arms": "Arms",
    "fullbody": "FullBody",
    "legs": "Legs",
    "fullbodystrength": "FREE WORKOUT #1",
    "fullbodystregth": "FREE WORKOUT #1",
    "sportnutrition": "FREE WORKOUT #2",
    "sportsnutrition": "FREE WORKOUT #2",
    "newcore": "Core",
    "newarms": "Arms",
    "newfullbody": "FullBody",
    "newlegs": "Legs",
    "freeworkout1": "FREE WORKOUT #1",
    "freeworkout2": "FREE WORKOUT #2",
}


def normalize_body_part(value: str | None) -> str | None:
    if value in (None, ""):
        return value
    value_text = str(value)
    key = re.sub(r"[^a-z0-9]", "", value_text.lower())
    if not key:
        return value_text
    return BODY_PART_ALIASES.get(key, value_text)


class VideoCreateRequest(BaseModel):
    body_part: str | None = None
    gender: str | None = None
    title: str | None = None
    description: str | None = None
    video_url: AnyHttpUrl
    thumbnail_url: AnyHttpUrl
    duration_seconds: int | None = Field(None, gt=0)
    requires_payment: bool = False

    @field_validator("body_part")
    @classmethod
    def validate_body_part(cls, value: str | None) -> str:
        if value in (None, ""):
            return ""
        normalized = normalize_body_part(value)
        allowed = {item.value for item in BodyPartEnum}
        if normalized not in allowed:
            raise ValueError("Input should be 'Core', 'Arms', 'FullBody', 'Legs', 'FREE WORKOUT #1' or 'FREE WORKOUT #2'")
        return normalized

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
    duration_seconds: int | None = Field(None, gt=0)
    requires_payment: bool | None = None

    @field_validator("body_part")
    @classmethod
    def validate_body_part(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return "" if value == "" else None
        normalized = normalize_body_part(value)
        allowed = {item.value for item in BodyPartEnum}
        if normalized not in allowed:
            raise ValueError("Input should be 'Core', 'Arms', 'FullBody', 'Legs', 'FREE WORKOUT #1' or 'FREE WORKOUT #2'")
        return normalized

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
    duration_seconds: int | None = None
    requires_payment: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
