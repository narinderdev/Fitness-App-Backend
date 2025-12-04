from datetime import date
from pydantic import BaseModel, field_validator


class ScanRequest(BaseModel):
    barcode: str


class FoodItemResponse(BaseModel):
    id: int | None = None
    barcode: str
    product_name: str | None = None
    brand: str | None = None
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    image_url: str | None = None

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
