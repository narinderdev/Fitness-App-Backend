from datetime import datetime

from pydantic import BaseModel


class ProgressPhotoResponse(BaseModel):
    id: int
    image_url: str
    taken_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
