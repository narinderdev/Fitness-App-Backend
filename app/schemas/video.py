from enum import Enum
from datetime import datetime
from pydantic import BaseModel, AnyHttpUrl


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
    body_part: BodyPartEnum
    gender: GenderEnum
    title: str | None = None
    description: str | None = None
    video_url: AnyHttpUrl
    thumbnail_url: AnyHttpUrl


class VideoUpdateRequest(BaseModel):
    body_part: BodyPartEnum | None = None
    gender: GenderEnum | None = None
    title: str | None = None
    description: str | None = None
    video_url: AnyHttpUrl | None = None
    thumbnail_url: AnyHttpUrl | None = None


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
