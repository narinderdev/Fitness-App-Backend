import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import ProfileResponse, ProfileUpdate
from app.services.auth_middleware import get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/profile", tags=["Profile"])
UPLOAD_DIR = Path("uploads/profile_photos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


@router.delete("/delete")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.is_active = False
        user.otp = None
        db.commit()

        return create_response(
            message="Account deleted successfully",
            data={"deleted": True},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if file.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

        extension = Path(file.filename).suffix.lower() or ".jpg"
        if extension not in {".jpg", ".jpeg", ".png"}:
            extension = ".jpg"

        filename = f"user_{user.id}_{int(time.time())}{extension}"
        file_path = UPLOAD_DIR / filename

        contents = await file.read()
        file_path.write_bytes(contents)

        user.photo = str(file_path)
        db.commit()
        db.refresh(user)

        profile_payload = ProfileResponse.model_validate(user).model_dump()
        return create_response(
            message="Profile photo uploaded successfully",
            data=profile_payload,
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)
