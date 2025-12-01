from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import RegisterRequest, RequestOtp, VerifyOtp, UserResponse
from app.services.email_services import send_email_otp
from app.services.auth_service import create_access_token
from app.database import get_db
import random
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/auth", tags=["Auth"])

# REGISTRATION - Step 1: send OTP
@router.post("/register")
def register_user(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

        otp = str(random.randint(100000, 999999))

        new_user = User(
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            otp=otp
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        send_email_otp(body.email, otp)
        return create_response(
            message="OTP sent for registration",
            data={"user_id": new_user.id, "email": new_user.email},
            status_code=status.HTTP_201_CREATED
        )
    except Exception as exc:
        return handle_exception(exc)

# REGISTRATION - Step 2: verify OTP
@router.post("/register/verify")
def verify_registration(body: VerifyOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email).first()
        if not user or user.otp != body.otp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        user.otp = None
        db.commit()
        db.refresh(user)

        user_payload = UserResponse.model_validate(user).model_dump()
        return create_response(
            message="Registration verified successfully",
            data=user_payload,
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)

# LOGIN - Step 1: request OTP
@router.post("/login/request-otp")
def request_login_otp(body: RequestOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not registered")

        otp = str(random.randint(100000, 999999))
        user.otp = otp
        db.commit()

        send_email_otp(body.email, otp)
        return create_response(
            message="OTP sent for login",
            data={"email": body.email},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)

# LOGIN - Step 2: verify OTP
@router.post("/login/verify")
def verify_login_otp(body: VerifyOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email).first()
        if not user or user.otp != body.otp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        user.otp = None
        db.commit()

        token = create_access_token({"sub": user.email})
        return create_response(
            message="Login successful",
            data={"access_token": token, "token_type": "bearer"},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)
