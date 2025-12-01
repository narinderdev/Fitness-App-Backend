from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str | None = None
    email: EmailStr

class RequestOtp(BaseModel):
    email: EmailStr

class VerifyOtp(BaseModel):
    email: EmailStr
    otp: str

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None
    email: EmailStr

    model_config = {"from_attributes": True}

class ProfileUpdate(BaseModel):
    phone: str | None = None
    dob: str | None = None
    gender: str | None = None
    photo: str | None = None  # base64 or URL


class ProfileResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None
    email: EmailStr
    phone: str | None
    dob: str | None
    gender: str | None
    photo: str | None

    model_config = {"from_attributes": True}
