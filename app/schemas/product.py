from datetime import datetime

from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    badge_text: str | None = None
    description: str | None = None
    image_url: str | None = None
    link_url: str | None = None
    is_active: bool
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    title: str
    subtitle: str | None = None
    badge_text: str | None = None
    description: str | None = None
    image_url: str | None = None
    link_url: str | None = None
    is_active: bool = True
    sort_order: int = 0


class ProductUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    badge_text: str | None = None
    description: str | None = None
    image_url: str | None = None
    link_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
