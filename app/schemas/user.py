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

class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    dob: str | None = None
    gender: str | None = None
    photo: str | None = None  # base64 or URL


class ProfileResponse(BaseModel):
    id: int
    first_name: str | None
    last_name: str | None
    email: EmailStr
    phone: str | None
    dob: str | None
    gender: str | None
    photo: str | None
    is_active: bool

    model_config = {"from_attributes": True}
