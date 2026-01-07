from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import ProfileResponse, UserFlagsUpdate
from app.utils.response import create_response, handle_exception
from app.services.auth_middleware import get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    try:
        base_query = db.query(User).filter(User.is_admin == False).order_by(User.id.asc())
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


@router.put("/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.is_admin and not is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate another admin")

        user.is_active = is_active
        db.commit()
        db.refresh(user)

        payload = ProfileResponse.model_validate(user).model_dump()
        message = "User activated successfully" if is_active else "User deactivated successfully"
        return create_response(
            message=message,
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.put("/{user_id}/flags")
def update_user_flags(
    user_id: int,
    payload: UserFlagsUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No flags provided",
            )

        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        payload = ProfileResponse.model_validate(user).model_dump()
        return create_response(
            message="User flags updated successfully",
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
