from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(settings.bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials  # Extract actual JWT token from header

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
