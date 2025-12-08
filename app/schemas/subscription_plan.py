from pydantic import BaseModel, Field


class SubscriptionPlanBase(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    duration_months: int = Field(..., gt=0)
    original_price: float = Field(..., gt=0)
    discounted_price: float = Field(..., gt=0)
    monthly_equivalent: float | None = Field(None, gt=0)
    billing_term: str | None = Field(None, max_length=100)
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    duration_months: int | None = Field(None, gt=0)
    original_price: float | None = Field(None, gt=0)
    discounted_price: float | None = Field(None, gt=0)
    monthly_equivalent: float | None = Field(None, gt=0)
    billing_term: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int

    class Config:
        from_attributes = True
