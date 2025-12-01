from pydantic import BaseModel, EmailStr

class RequestOtp(BaseModel):
    email: EmailStr

class VerifyOtp(BaseModel):
    email: EmailStr
    otp: str

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
