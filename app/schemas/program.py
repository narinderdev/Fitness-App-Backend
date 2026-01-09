from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProgramVisibility(str, Enum):
    free = "free"
    paid = "paid"


class ProgramBase(BaseModel):
    slug: str = Field(..., min_length=2, max_length=120)
    title: str = Field(..., min_length=3, max_length=150)
    subtitle: str | None = Field(None, max_length=200)
    description: str | None = None
    duration_days: int = Field(..., gt=0)
    workouts_per_week: int = Field(5, ge=0, le=7)
    rest_days_per_week: int = Field(2, ge=0, le=7)
    level: str | None = Field(None, max_length=50)
    access_level: ProgramVisibility = ProgramVisibility.free
    price_usd: float | None = Field(None, ge=0)
    weekly_price_usd: float | None = Field(None, ge=0)
    weekly_original_price_usd: float | None = Field(None, ge=0)
    monthly_price_usd: float | None = Field(None, ge=0)
    monthly_original_price_usd: float | None = Field(None, ge=0)
    yearly_price_usd: float | None = Field(None, ge=0)
    yearly_original_price_usd: float | None = Field(None, ge=0)
    cta_label: str | None = Field(None, max_length=120)
    hero_image_url: str | None = None
    cover_image_url: str | None = None
    is_featured: bool = False
    is_active: bool = True


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    slug: str | None = Field(None, min_length=2, max_length=120)
    title: str | None = Field(None, min_length=3, max_length=150)
    subtitle: str | None = Field(None, max_length=200)
    description: str | None = None
    duration_days: int | None = Field(None, gt=0)
    workouts_per_week: int | None = Field(None, ge=0, le=7)
    rest_days_per_week: int | None = Field(None, ge=0, le=7)
    level: str | None = Field(None, max_length=50)
    access_level: ProgramVisibility | None = None
    price_usd: float | None = Field(None, ge=0)
    weekly_price_usd: float | None = Field(None, ge=0)
    weekly_original_price_usd: float | None = Field(None, ge=0)
    monthly_price_usd: float | None = Field(None, ge=0)
    monthly_original_price_usd: float | None = Field(None, ge=0)
    yearly_price_usd: float | None = Field(None, ge=0)
    yearly_original_price_usd: float | None = Field(None, ge=0)
    cta_label: str | None = Field(None, max_length=120)
    hero_image_url: str | None = None
    cover_image_url: str | None = None
    is_featured: bool | None = None
    is_active: bool | None = None


class ProgramDayBase(BaseModel):
    day_number: int = Field(..., gt=0)
    title: str = Field(..., min_length=3, max_length=150)
    focus: str | None = Field(None, max_length=100)
    description: str | None = None
    is_rest_day: bool = False
    workout_summary: str | None = None
    duration_minutes: int | None = Field(None, gt=0)
    video_id: int | None = Field(None, gt=0)
    tips: str | None = None


class ProgramDayCreate(ProgramDayBase):
    pass


class ProgramDayUpdate(BaseModel):
    day_number: int | None = Field(None, gt=0)
    title: str | None = Field(None, min_length=3, max_length=150)
    focus: str | None = Field(None, max_length=100)
    description: str | None = None
    is_rest_day: bool | None = None
    workout_summary: str | None = None
    duration_minutes: int | None = Field(None, gt=0)
    video_id: int | None = Field(None, gt=0)
    tips: str | None = None


class ProgramDayPreview(BaseModel):
    day_number: int
    title: str
    focus: str | None = None
    is_rest_day: bool


class ProgramVideoSnippet(BaseModel):
    id: int
    title: str | None = None
    thumbnail_url: str | None = None
    video_url: str | None = None


class ProgramDayResponse(ProgramDayBase):
    id: int
    program_id: int
    created_at: datetime
    updated_at: datetime
    video: ProgramVideoSnippet | None = None
    is_completed: bool = False
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProgramResponse(ProgramBase):
    id: int
    created_at: datetime
    updated_at: datetime
    days_count: int
    requires_payment: bool
    preview_days: List[ProgramDayPreview] = []

    model_config = {"from_attributes": True}


class ProgramTimeline(BaseModel):
    total_days: int
    workouts: int
    rest_days: int


class ProgramDetailResponse(BaseModel):
    program: ProgramResponse
    days: List[ProgramDayResponse]
    timeline: ProgramTimeline
    available_day: int | None = None
    start_date: date | None = None


class ProgramScheduleDay(BaseModel):
    day_number: int = Field(..., gt=0)
    is_rest_day: bool = False
    title: str | None = None
    focus: str | None = Field(None, max_length=100)
    description: str | None = None
    workout_summary: str | None = None
    duration_minutes: int | None = Field(None, gt=0)
    video_id: int | None = Field(None, gt=0)
    tips: str | None = None


class ProgramScheduleUpdate(BaseModel):
    days: List[ProgramScheduleDay]
