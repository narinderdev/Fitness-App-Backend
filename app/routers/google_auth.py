from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.services.google_auth_service import google_oauth
from app.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth_service import create_access_token
import uuid
import os

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])


@router.get("/login")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await google_oauth.authorize_redirect(request, redirect_uri)



@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await google_oauth.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid Google token")

        email = user_info["email"]
        name = user_info.get("name")
        picture = user_info.get("picture")

        # ---- check or create user ----
        user = db.query(User).filter(User.email == email).first()

        if not user:
            user = User(
                email=email,
                first_name=name.split(" ")[0] if name else None,
                last_name=" ".join(name.split(" ")[1:]) if name and len(name.split(" ")) > 1 else None,
                is_active=True,
                otp=None
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # ---- generate JWT ----
        jti = str(uuid.uuid4())
        token = create_access_token({"sub": user.email, "jti": jti})

        # ---- user session ----
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

        profile_complete = bool(user.first_name and user.last_name)

        return {
            "message": "Google login success",
            "access_token": token,
            "token_type": "bearer",
            "profile_complete": profile_complete,
            "user": {
                "email": user.email,
                "name": name,
                "picture": picture
            }
        }

    except Exception as e:
        print("Google Auth Error:", e)
        raise HTTPException(status_code=500, detail="Google authentication failed")
