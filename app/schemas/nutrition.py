from datetime import date
from typing import List, Optional
from pydantic import BaseModel, field_validator, Field


class ScanRequest(BaseModel):
    barcode: str

class FoodItemResponse(BaseModel):
    id: Optional[int] = None
    barcode: Optional[str] = None
    product_name: str
    brand: str | None = None
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    image_url: str | None = None
    description: str | None = None
    source: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    is_active: bool | None = None

    model_config = {"from_attributes": True}


class LogCreate(BaseModel):
    barcode: str | None = None
    food_item_id: int | None = None
    servings: float = 1.0
    notes: str | None = None
    consumed_date: str | None = None

    @field_validator("consumed_date")
    @classmethod
    def validate_date(cls, value):
        if value is None:
            return None
        date.fromisoformat(value)
        return value


class FoodLogEntry(BaseModel):
    id: int
    consumed_date: str
    servings: float
    calories: float | None
    protein: float | None
    carbs: float | None
    fat: float | None
    notes: str | None
    food_item: FoodItemResponse | None

    model_config = {"from_attributes": True}


class FoodCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class FoodCategoryCreate(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True


class FoodCategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class FoodItemAdminPayload(BaseModel):
    name: str = Field(..., alias="product_name")
    brand: str | None = None
    calories: float
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    image_url: str | None = None
    description: str | None = None
    category_id: int | None = None
    is_active: bool = True

    @field_validator("calories")
    @classmethod
    def validate_calories(cls, value):
        if value is None:
            raise ValueError("calories is required")
        if value < 0:
            raise ValueError("calories must be non-negative")
        return value

    class Config:
        allow_population_by_field_name = True
