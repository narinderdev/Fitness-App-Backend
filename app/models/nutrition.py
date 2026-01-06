from datetime import datetime, date

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    foods = relationship("FoodItem", back_populates="category")


class MealConfig(Base):
    __tablename__ = "meal_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    icon_url = Column(String, nullable=True)
    min_ratio = Column(Float, default=0.0, nullable=False)
    max_ratio = Column(Float, default=0.0, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class FoodItem(Base):
    __tablename__ = "food_items"
    __table_args__ = (UniqueConstraint("barcode", name="uq_food_barcode"),)

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, nullable=True, unique=True, index=True)
    product_name = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    serving_quantity = Column(Float, nullable=True)
    serving_unit = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    source = Column(String, default="openfoodfacts", nullable=False)
    last_synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    category_id = Column(Integer, ForeignKey("food_categories.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    category = relationship("FoodCategory", back_populates="foods")
    logs = relationship("FoodLog", back_populates="food_item")


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    food_item_id = Column(Integer, ForeignKey("food_items.id", ondelete="SET NULL"), nullable=True)
    barcode = Column(String, nullable=True)
    serving_multiplier = Column(Float, default=1.0, nullable=False)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    meal_type = Column(String, nullable=True, index=True)
    consumed_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    food_item = relationship("FoodItem", back_populates="logs")
