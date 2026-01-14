from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator, model_validator, Field


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
    food_type: str | None = None
    fdc_id: int | None = None
    calories_per_100g: float | None = None
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    default_serving_name: str | None = None
    default_serving_grams: float | None = None
    density_g_per_ml: float | None = None
    default_serving_ml: float | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    serving_grams: float | None = None
    image_url: str | None = None
    description: str | None = None
    source: str | None = None
    source_item_id: str | None = None
    last_verified_at: datetime | None = None
    category_id: int | None = None
    category_name: str | None = None
    is_active: bool | None = None

    model_config = {"from_attributes": True}


class WishlistCreate(BaseModel):
    food_item_id: int | None = None
    barcode: str | None = None


class WishlistItemResponse(BaseModel):
    id: int
    created_at: str
    food_item: FoodItemResponse

    model_config = {"from_attributes": True}


class LogCreate(BaseModel):
    barcode: str | None = None
    food_item_id: int | None = None
    servings: float = 1.0
    notes: str | None = None
    consumed_date: str | None = None
    meal_type: str | None = None

    @field_validator("consumed_date")
    @classmethod
    def validate_date(cls, value):
        if value is None:
            return None
        date.fromisoformat(value)
        return value

    @field_validator("meal_type")
    @classmethod
    def normalize_meal_type(cls, value):
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


class LogUpdate(BaseModel):
    servings: float
    notes: str | None = None

    @field_validator("servings")
    @classmethod
    def validate_servings(cls, value):
        if value <= 0:
            raise ValueError("servings must be positive")
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
    meal_type: str | None
    food_item: FoodItemResponse | None

    model_config = {"from_attributes": True}


class FoodCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class FoodCategoryCreate(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True


class FoodCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class FoodItemAdminPayload(BaseModel):
    name: str = Field(..., alias="product_name")
    brand: str | None = None
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    food_type: str | None = None
    fdc_id: int | None = None
    calories_per_100g: float | None = None
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    default_serving_name: str | None = None
    default_serving_grams: float | None = None
    density_g_per_ml: float | None = None
    default_serving_ml: float | None = None
    serving_quantity: float | None = None
    serving_unit: str | None = None
    serving_grams: float | None = None
    image_url: str | None = None
    description: str | None = None
    category_id: int | None = None
    is_active: bool = True
    source: str | None = None
    source_item_id: str | None = None

    @field_validator("calories", "calories_per_100g")
    @classmethod
    def validate_calories(cls, value):
        if value is None:
            return value
        if value < 0:
            raise ValueError("calories must be non-negative")
        return value

    @field_validator("food_type")
    @classmethod
    def normalize_food_type(cls, value):
        if value is None:
            return value
        normalized = value.strip().upper()
        if normalized not in {"SOLID", "LIQUID"}:
            raise ValueError("food_type must be 'SOLID' or 'LIQUID'")
        return normalized

    @field_validator("default_serving_grams", "density_g_per_ml", "default_serving_ml")
    @classmethod
    def validate_positive_values(cls, value):
        if value is None:
            return value
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    @field_validator("default_serving_name")
    @classmethod
    def validate_serving_name(cls, value):
        if value is None:
            return value
        trimmed = value.strip()
        return trimmed or None

    @field_validator("serving_grams")
    @classmethod
    def validate_serving_grams(cls, value):
        if value is None:
            return value
        if value <= 0:
            raise ValueError("serving_grams must be positive")
        return value

    @model_validator(mode="after")
    def validate_nutrition(self):
        if self.calories_per_100g is None:
            raise ValueError("calories_per_100g is required")
        if self.food_type == "SOLID" and self.default_serving_grams is None:
            raise ValueError("default_serving_grams is required for solids")
        if self.food_type == "LIQUID":
            if self.density_g_per_ml is None:
                raise ValueError("density_g_per_ml is required for liquids")
            if self.default_serving_ml is None:
                raise ValueError("default_serving_ml is required for liquids")
        if self.food_type in {"SOLID", "LIQUID"} and not self.default_serving_name:
            raise ValueError("default_serving_name is required")
        return self

    class Config:
        allow_population_by_field_name = True


class MealConfigResponse(BaseModel):
    id: int
    key: str
    name: str
    icon_url: str | None = None
    min_ratio: float
    max_ratio: float
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class MealConfigCreate(BaseModel):
    key: str
    name: str
    icon_url: str | None = None
    min_ratio: float = 0.0
    max_ratio: float = 0.0
    sort_order: int = 0
    is_active: bool = True

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value):
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("key is required")
        return normalized


class MealConfigUpdate(BaseModel):
    key: str | None = None
    name: str | None = None
    icon_url: str | None = None
    min_ratio: float | None = None
    max_ratio: float | None = None
    sort_order: int | None = None
    is_active: bool | None = None

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value):
        if value is None:
            return None
        normalized = value.strip().lower().replace(" ", "_")
        return normalized or None
