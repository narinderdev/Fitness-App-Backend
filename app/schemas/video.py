from enum import Enum
from pydantic import BaseModel


class GenderEnum(str, Enum):
    male = "Male"
    female = "Female"
    both = "Both"


class BodyPartEnum(str, Enum):
    new_core = "NewCore"
    new_arms = "NewArms"
    new_full_body = "NewFullBody"
    new_legs = "NewLegs"


class VideoResponse(BaseModel):
    id: int
    title: str | None = None
    description: str | None = None
    body_part: str
    gender: str
    video_url: str
    thumbnail_url: str
    created_at: str

    model_config = {"from_attributes": True}
