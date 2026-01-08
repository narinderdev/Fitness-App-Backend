import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.progress_photo import ProgressPhoto
from app.models.user import User
from app.schemas.progress_photo import ProgressPhotoResponse
from app.services.auth_middleware import get_current_user
from app.services.spaces_service import upload_progress_photo
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/progress-photos", tags=["Progress Photos"])


@router.get("")
def list_progress_photos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        photos = (
            db.query(ProgressPhoto)
            .filter(ProgressPhoto.user_id == current_user.id)
            .order_by(ProgressPhoto.taken_at.desc())
            .all()
        )
        payload = [ProgressPhotoResponse.model_validate(photo).model_dump() for photo in photos]
        return create_response(
            message="Progress photos fetched",
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("")
async def create_progress_photo(
    file: UploadFile = File(...),
    taken_at: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if file.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

        parsed_taken_at = None
        if taken_at:
            try:
                normalized = taken_at.replace("Z", "+00:00") if taken_at.endswith("Z") else taken_at
                parsed_taken_at = datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid timestamp format",
                ) from exc

        extension = Path(file.filename).suffix.lower() or ".jpg"
        if extension not in {".jpg", ".jpeg", ".png"}:
            extension = ".jpg"

        timestamp = int((parsed_taken_at or datetime.utcnow()).timestamp())
        filename = f"user_{current_user.id}_{timestamp}_{uuid.uuid4().hex[:8]}{extension}"

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file upload")

        url = upload_progress_photo(contents, filename, content_type=file.content_type)
        photo = ProgressPhoto(
            user_id=current_user.id,
            image_url=url,
            taken_at=parsed_taken_at or datetime.utcnow(),
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)

        payload = ProgressPhotoResponse.model_validate(photo).model_dump()
        return create_response(
            message="Progress photo uploaded",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)
