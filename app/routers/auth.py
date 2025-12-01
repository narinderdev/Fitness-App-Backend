from datetime import datetime
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.user import RequestOtp, VerifyOtp
from app.services.email_services import send_email_otp
from app.services.auth_service import create_access_token
from app.services.auth_middleware import get_current_session
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/auth", tags=["Auth"])

# Unified OTP request for registration + login
@router.post("/otp/request")
def request_otp(body: RequestOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email).first()
        otp = str(random.randint(100000, 999999))
        flow = "login"

        if user:
            user.otp = otp
            if not user.is_active:
                user.is_active = True
                flow = "reactivated"
            elif not user.first_name:
                flow = "register"
            db.commit()
            db.refresh(user)
        else:
            user = User(email=body.email, otp=otp)
            db.add(user)
            db.commit()
            db.refresh(user)
            flow = "register"

        send_email_otp(body.email, otp)
        return create_response(
            message="OTP sent successfully",
            data={"email": body.email, "flow": flow},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/otp/resend")
def resend_otp(body: RequestOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        otp = str(random.randint(100000, 999999))
        user.otp = otp
        if not user.is_active:
            user.is_active = True
        db.commit()

        send_email_otp(body.email, otp)
        flow = "register" if not user.first_name else "login"
        return create_response(
            message="OTP resent successfully",
            data={"email": body.email, "flow": flow},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/otp/verify")
def verify_otp(body: VerifyOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email, User.is_active == True).first()
        if not user or user.otp != body.otp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        user.otp = None
        jti = str(uuid.uuid4())
        token = create_access_token({"sub": user.email, "jti": jti})

        session_record = (
            db.query(UserSession)
            .filter(UserSession.user_id == user.id)
            .order_by(UserSession.id.asc())
            .first()
        )

        if session_record:
            session_record.jti = jti
            session_record.token = token
            session_record.is_active = True
            session_record.revoked_at = None
        else:
            session_record = UserSession(user_id=user.id, jti=jti, token=token)
            db.add(session_record)

        db.commit()
        db.refresh(user)

        profile_complete = bool(user.first_name and user.last_name)

        return create_response(
            message="OTP verified successfully",
            data={
                "access_token": token,
                "token_type": "bearer",
                "profile_complete": profile_complete
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/logout")
def logout_user(auth_context=Depends(get_current_session)):
    try:
        session = auth_context["session"]
        db: Session = auth_context["db"]
        user: User = auth_context["user"]

        session.is_active = False
        session.revoked_at = datetime.utcnow()
        session.token = None
        db.commit()

        return create_response(
            message="Logout successful",
            data={"user_id": user.id, "session_id": session.id},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)
