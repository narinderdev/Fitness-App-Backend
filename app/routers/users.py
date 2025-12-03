from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import ProfileResponse
from app.utils.response import create_response, handle_exception
from app.services.auth_middleware import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        base_query = db.query(User).order_by(User.id.asc())
        total = base_query.count()
        users = base_query.offset((page - 1) * page_size).limit(page_size).all()
        payload = [
            ProfileResponse.model_validate(user).model_dump()
            for user in users
        ]
        return create_response(
            message="Users fetched successfully",
            data={
                "page": page,
                "page_size": page_size,
                "count": len(payload),
                "total": total,
                "has_next": page * page_size < total,
                "users": payload
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
