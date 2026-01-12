from pydantic import BaseModel, EmailStr

from enum import Enum

from pydantic import BaseModel, EmailStr


class PlatformEnum(str, Enum):
    app = "app"
    web = "web"


class RequestOtp(BaseModel):
    email: EmailStr
    is_admin: bool = False
    platform: PlatformEnum = PlatformEnum.app

class VerifyOtp(BaseModel):
    email: EmailStr
    otp: str
    is_admin: bool = False
    platform: PlatformEnum = PlatformEnum.app


class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    dob: str | None = None
    gender: str | None = None
    photo: str | None = None  # base64 or URL
    bmi_value: float | None = None
    bmi_category: str | None = None
    daily_step_goal: int | None = None
    daily_water_goal_ml: int | None = None


class ProfileResponse(BaseModel):
    id: int
    first_name: str | None
    last_name: str | None
    email: EmailStr
    phone: str | None
    dob: str | None
    gender: str | None
    photo: str | None
    bmi_value: float | None
    bmi_category: str | None
    daily_step_goal: int | None
    daily_water_goal_ml: int | None
    is_active: bool
    is_admin: bool
    has_pilates_board: bool
    has_ankle_wrist_weights: bool

    model_config = {"from_attributes": True}


class UserFlagsUpdate(BaseModel):
    has_pilates_board: bool | None = None
    has_ankle_wrist_weights: bool | None = None
