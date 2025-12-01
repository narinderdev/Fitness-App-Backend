import uuid
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.video import Video
from app.schemas.video import VideoResponse, BodyPartEnum, GenderEnum
from app.services.auth_middleware import get_current_user
from app.services.spaces_service import (
    get_videos_by_category,
    normalize_category,
    upload_category_video,
    upload_category_thumbnail,
)
from app.utils.response import create_response, handle_exception

router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
    dependencies=[Depends(get_current_user)],
)

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/mpeg", "video/quicktime"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}
BODY_PART_VALUES = {bp.value for bp in BodyPartEnum}


def _safe_filename(body_part: str, original_name: str, fallback_ext: str) -> str:
    extension = Path(original_name).suffix or fallback_ext
    return f"{body_part.lower()}_{uuid.uuid4().hex}{extension.lower()}"


def _resolve_category(category: str) -> str | None:
    normalized = normalize_category(category)
    if not normalized and category in BODY_PART_VALUES:
        normalized = category
    return normalized


@router.get("/db/{category}")
def fetch_db_videos(category: str, db: Session = Depends(get_db)):
    try:
        normalized = _resolve_category(category)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

        stored_videos = (
            db.query(Video)
            .filter(Video.body_part == normalized)
            .order_by(Video.created_at.desc())
            .all()
        )

        payload = [
            VideoResponse.model_validate(video).model_dump()
            for video in stored_videos
        ]

        return create_response(
            message="Videos fetched from database",
            data={
                "category": normalized,
                "source": "database",
                "count": len(payload),
                "videos": payload,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/spaces/{category}")
def fetch_spaces_videos(category: str):
    try:
        normalized = _resolve_category(category)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

        remote_videos = get_videos_by_category(normalized)
        return create_response(
            message="Videos fetched from DigitalOcean Spaces",
            data={
                "category": normalized,
                "source": "spaces",
                "count": len(remote_videos),
                "videos": remote_videos,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/upload")
async def upload_video(
    body_part: BodyPartEnum = Form(...),
    gender: GenderEnum = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    video_file: UploadFile = File(...),
    thumbnail_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        video_type = video_file.content_type or ""
        thumb_type = thumbnail_file.content_type or ""

        if video_type.lower() not in ALLOWED_VIDEO_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported video format")

        if thumb_type.lower() not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported thumbnail format")

        normalized_body_part = body_part.value

        video_filename = _safe_filename(normalized_body_part, video_file.filename or "video.mp4", ".mp4")
        thumbnail_filename = _safe_filename(normalized_body_part, thumbnail_file.filename or "thumbnail.jpg", ".jpg")

        video_bytes = await video_file.read()
        thumbnail_bytes = await thumbnail_file.read()

        video_url = upload_category_video(video_bytes, video_filename, normalized_body_part, video_type)
        thumbnail_url = upload_category_thumbnail(thumbnail_bytes, thumbnail_filename, normalized_body_part, thumb_type)

        new_video = Video(
            title=title,
            description=description,
            body_part=normalized_body_part,
            gender=gender.value,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)

        payload = VideoResponse.model_validate(new_video).model_dump()
        return create_response(
            message="Video uploaded successfully",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.put("/{video_id}")
async def update_video(
    video_id: int,
    body_part: BodyPartEnum | None = Form(None),
    gender: GenderEnum | None = Form(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    video_file: UploadFile | None = File(None),
    thumbnail_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

        if body_part:
            video.body_part = body_part.value
        if gender:
            video.gender = gender.value
        if title is not None:
            video.title = title
        if description is not None:
            video.description = description

        if video_file:
            if (video_file.content_type or "").lower() not in ALLOWED_VIDEO_TYPES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported video format")
            new_video_filename = _safe_filename(video.body_part, video_file.filename or "video.mp4", ".mp4")
            video_bytes = await video_file.read()
            video.video_url = upload_category_video(video_bytes, new_video_filename, video.body_part, video_file.content_type)

        if thumbnail_file:
            if (thumbnail_file.content_type or "").lower() not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported thumbnail format")
            new_thumb_filename = _safe_filename(video.body_part, thumbnail_file.filename or "thumbnail.jpg", ".jpg")
            thumbnail_bytes = await thumbnail_file.read()
            video.thumbnail_url = upload_category_thumbnail(
                thumbnail_bytes, new_thumb_filename, video.body_part, thumbnail_file.content_type
            )

        db.commit()
        db.refresh(video)

        payload = VideoResponse.model_validate(video).model_dump()
        return create_response(
            message="Video updated successfully",
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

        db.delete(video)
        db.commit()

        return create_response(
            message="Video deleted successfully",
            data={"deleted": True, "video_id": video_id},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
