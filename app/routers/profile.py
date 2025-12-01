from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import ProfileResponse, ProfileUpdate
from app.services.auth_middleware import get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        profile_payload = ProfileResponse.model_validate(user).model_dump()
        return create_response(
            message="Profile fetched successfully",
            data=profile_payload,
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)


@router.put("/update")
def update_profile(
    update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        profile_payload = ProfileResponse.model_validate(user).model_dump()
        return create_response(
            message="Profile updated successfully",
            data=profile_payload,
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)
