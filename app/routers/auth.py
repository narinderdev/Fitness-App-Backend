from datetime import datetime
import random
import uuid

from jose import jwt, JWTError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.models.water import DeviceToken
from app.schemas.user import RequestOtp, VerifyOtp, RefreshTokenRequest, PlatformEnum
from app.services.gmail_oauth_service import send_email_otp
from app.services.auth_service import create_access_token, create_refresh_token
from app.services.auth_middleware import get_current_session
from app.services.questionnaire_service import count_pending_required_questions
from app.services.referral_service import normalize_referral_code, ensure_referral_code
from app.services.firebase_service import send_push_notification
from app.utils.response import create_response, handle_exception
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# Unified OTP request for registration + login
@router.post("/otp/request")
def request_otp(body: RequestOtp, db: Session = Depends(get_db)):
    try:
        print("📩 OTP Request Received for:", body.email)

        user = db.query(User).filter(User.email == body.email).first()
        is_admin_request = body.is_admin
        platform = body.platform.value if isinstance(body.platform, PlatformEnum) else body.platform

        if is_admin_request:
            if not user or not user.is_admin:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
            if platform != PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only login via web")
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have been deactivated by admin")
        else:
            if user and user.is_admin and platform != PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only login via web")
            if user and not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have been deactivated by admin")

        if platform == PlatformEnum.web.value and not is_admin_request:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Web OTPs reserved for admins")

        otp = str(random.randint(100000, 999999))
        print("🔢 Generated OTP:", otp)

        flow = "login"

        if user:
            print("👤 Existing user found:", user.email)
            was_verified = user.otp is None
            user.otp = otp
            ensure_referral_code(db, user)

            if not user.is_active:
                print("⚠️ User not active — reactivating")
                user.is_active = True
                flow = "reactivated"

            elif not was_verified:
                print("🆕 User not verified yet — registration flow")
                flow = "register"

            db.commit()
            db.refresh(user)

        else:
            print("🆕 Creating new user:", body.email)
            if platform == PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Web registrations are disabled")
            user = User(email=body.email, otp=otp)
            referral_code = normalize_referral_code(body.referral_code)
            if referral_code:
                referrer = db.query(User).filter(User.referral_code == referral_code).first()
                if referrer:
                    user.referred_by_id = referrer.id
            db.add(user)
            db.commit()
            db.refresh(user)
            flow = "register"
            ensure_referral_code(db, user)
            db.commit()

        print("📨 Sending OTP Email...")
        send_email_otp(body.email, otp)

        print("✅ OTP email sent successfully!")

        return create_response(
            message="OTP sent successfully",
            data={"email": body.email, "flow": flow},
            status_code=status.HTTP_200_OK
        )

    except Exception as exc:
        print("❌ ERROR in request_otp:", exc)
        return handle_exception(exc)


@router.post("/otp/resend")
def resend_otp(body: RequestOtp, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == body.email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        platform = body.platform.value if isinstance(body.platform, PlatformEnum) else body.platform

        if body.is_admin:
            if not user.is_admin:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
            if platform != PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only login via web")
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have been deactivated by admin")
        else:
            if user.is_admin and platform != PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only login via web")
            if platform == PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Web OTPs reserved for admins")
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have been deactivated by admin")

        otp = str(random.randint(100000, 999999))
        was_verified = user.otp is None
        user.otp = otp
        if not user.is_active:
            user.is_active = True
        db.commit()

        send_email_otp(body.email, otp)
        flow = "login" if was_verified else "register"
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

        platform = body.platform.value if isinstance(body.platform, PlatformEnum) else body.platform

        if body.is_admin:
            if not user.is_admin:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
            if platform != PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only login via web")
        else:
            if user.is_admin and platform != PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only login via web")
            if platform == PlatformEnum.web.value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Web OTPs reserved for admins")

        user.otp = None
        jti = str(uuid.uuid4())
        token = create_access_token({"sub": user.email, "jti": jti})
        refresh_token = create_refresh_token({"sub": user.email, "jti": jti})

        session_record = UserSession(user_id=user.id, jti=jti, token=token)
        db.add(session_record)

        db.commit()
        db.refresh(user)
        ensure_referral_code(db, user)
        db.commit()

        if body.referral_code and not user.referred_by_id:
            referral_code = normalize_referral_code(body.referral_code)
            if referral_code:
                referrer = db.query(User).filter(User.referral_code == referral_code).first()
                if referrer and referrer.id != user.id:
                    user.referred_by_id = referrer.id
                    db.commit()

        _maybe_send_referral_reward(db, user)

        profile_complete = bool(user.first_name and user.last_name)
        pending_question_count = count_pending_required_questions(db, user)

        return create_response(
            message="OTP verified successfully",
            data={
                "access_token": token,
                "token_type": "bearer",
                "refresh_token": refresh_token,
                "profile_complete": profile_complete,
                "pending_question_count": pending_question_count,
                "has_pending_questions": pending_question_count > 0,
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)


def _maybe_send_referral_reward(db: Session, referred_user: User) -> None:
    if not referred_user.referred_by_id or referred_user.referral_reward_sent:
        return

    referrer = (
        db.query(User)
        .filter(User.id == referred_user.referred_by_id, User.is_active == True)
        .first()
    )
    if not referrer:
        return

    tokens = [token.token for token in referrer.device_tokens]
    if not tokens:
        return

    coupon_code = settings.REFERRAL_COUPON_CODE
    title = settings.REFERRAL_NOTIFICATION_TITLE
    body = settings.REFERRAL_NOTIFICATION_BODY.format(code=coupon_code)
    result = send_push_notification(
        tokens,
        title,
        body,
        data={
            "type": "referral_reward",
            "coupon_code": coupon_code,
            "referred_email": referred_user.email,
        },
    )
    invalid_tokens = result.get("invalid_tokens") or []
    if invalid_tokens:
        (
            db.query(DeviceToken)
            .filter(DeviceToken.token.in_(invalid_tokens))
            .delete(synchronize_session=False)
        )
    referred_user.referral_reward_sent = True
    db.commit()


@router.post("/refresh")
def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        try:
            payload = jwt.decode(
                body.refresh_token,
                settings.JWT_SECRET,
                algorithms=[settings.ALGORITHM],
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        email = payload.get("sub")
        jti = payload.get("jti")
        if not email or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        session = db.query(UserSession).filter(
            UserSession.jti == jti,
            UserSession.is_active == True,
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or logged out",
            )

        user = db.query(User).filter(
            User.email == email,
            User.is_active == True,
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive",
            )

        access_token = create_access_token({"sub": user.email, "jti": jti})
        new_refresh_token = create_refresh_token({"sub": user.email, "jti": jti})
        session.token = access_token
        db.commit()

        return create_response(
            message="Token refreshed",
            data={
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
            },
            status_code=status.HTTP_200_OK,
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
