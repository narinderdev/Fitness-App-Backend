from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.user_session import UserSession


def _get_auth_context(token: str, db: Session):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        jti = payload.get("jti")
        token_type = payload.get("type") or "access"
        if not email or not jti:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    session = db.query(UserSession).filter(
        UserSession.jti == jti,
        UserSession.is_active == True
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Session expired or logged out")

    user = db.query(User).filter(User.email == email, User.is_active == True).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found or inactive")

    return {"user": user, "session": session, "payload": payload}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(settings.bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    auth_context = _get_auth_context(token, db)
    return auth_context["user"]


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(settings.bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    auth_context = _get_auth_context(token, db)
    user = auth_context["user"]
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(settings.bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    context = _get_auth_context(token, db)
    context["token"] = token
    context["db"] = db
    return context
