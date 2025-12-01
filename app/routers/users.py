from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import ProfileResponse
from app.utils.response import create_response, handle_exception
from app.services.auth_middleware import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        users = db.query(User).order_by(User.id.asc()).all()
        payload = [
            ProfileResponse.model_validate(user).model_dump()
            for user in users
        ]
        return create_response(
            message="Users fetched successfully",
            data={"count": len(payload), "users": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
