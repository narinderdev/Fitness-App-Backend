from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.video import Video
from app.models.program import ProgramDay
from app.schemas.video import (
    VideoResponse,
    BodyPartEnum,
    GenderEnum,
    VideoCreateRequest,
    VideoUpdateRequest,
)
from app.services.spaces_service import (
    get_videos_by_category,
    normalize_category,
)
from app.utils.response import create_response, handle_exception

from app.services.auth_middleware import get_current_user, get_current_admin

router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
)

BODY_PART_VALUES = {bp.value for bp in BodyPartEnum}
CATEGORY_DB_ALIASES = {
    "Core": ["Core", "NewCore"],
    "Arms": ["Arms", "NewArms"],
    "FullBody": ["FullBody", "NewFullBody"],
    "Legs": ["Legs", "NewLegs"],
    "FullBodyStrength": ["FullBodyStrength"],
    "SportNutrition": ["SportNutrition"],
}
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _resolve_category(category: str) -> str | None:
    normalized = normalize_category(category)
    if not normalized and category in BODY_PART_VALUES:
        normalized = category
    return normalized


def _db_values_for_category(category: str) -> list[str]:
    return CATEGORY_DB_ALIASES.get(category, [category])


def _pagination_meta(page: int, page_size: int, total: int, count: int) -> dict:
    return {
        "page": page,
        "page_size": page_size,
        "count": count,
        "total": total,
        "has_next": page * page_size < total,
    }


def _build_category_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in CATEGORY_DB_ALIASES.items():
        for alias in aliases:
            normalized = alias.strip().lower()
            if normalized:
                lookup[normalized] = canonical
        lookup[canonical.strip().lower()] = canonical
    return lookup


_CATEGORY_ALIAS_LOOKUP = _build_category_alias_lookup()


def _category_key(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "Uncategorized"
    normalized = raw.lower()
    mapped = _CATEGORY_ALIAS_LOOKUP.get(normalized)
    if mapped:
        return mapped
    normalized_from_slug = normalize_category(raw)
    if normalized_from_slug:
        return normalized_from_slug
    return raw


def _category_counts(query) -> dict[str, int]:
    rows = (
        query.with_entities(Video.body_part, func.count(Video.id))
        .group_by(Video.body_part)
        .all()
    )
    counts: dict[str, int] = {}
    for body_part, count in rows:
        key = _category_key(body_part)
        counts[key] = counts.get(key, 0) + int(count or 0)
    return counts


@router.get("/db/{category}")
def fetch_db_videos(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        requesting_all = category.strip().lower() == "all"
        normalized = None if requesting_all else _resolve_category(category)
        if not requesting_all and not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

        plan_video_subquery = (
            db.query(ProgramDay.video_id)
            .filter(ProgramDay.video_id.isnot(None))
            .subquery()
        )

        all_query = db.query(Video).filter(~Video.id.in_(plan_video_subquery))
        category_counts = _category_counts(all_query)
        base_query = all_query.order_by(Video.created_at.desc())
        if normalized:
            db_values = _db_values_for_category(normalized)
            base_query = base_query.filter(Video.body_part.in_(db_values))

        total = base_query.count()
        stored_videos = (
            base_query.offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        payload = [
            VideoResponse.model_validate(video).model_dump()
            for video in stored_videos
        ]

        return create_response(
            message="Videos fetched from database",
            data={
                "category": "all" if requesting_all else normalized,
                "source": "database",
                **_pagination_meta(page, page_size, total, len(payload)),
                "category_counts": category_counts,
                "videos": payload,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/spaces/{category}")
def fetch_spaces_videos(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user=Depends(get_current_user),
):
    try:
        normalized = _resolve_category(category)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

        remote_videos = get_videos_by_category(normalized)
        total = len(remote_videos)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = remote_videos[start:end]
        return create_response(
            message="Videos fetched from DigitalOcean Spaces",
            data={
                "category": normalized,
                "source": "spaces",
                **_pagination_meta(page, page_size, total, len(paginated)),
                "videos": paginated,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/upload")
def upload_video(
    payload: VideoCreateRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        new_video = Video(
            title=payload.title,
            description=payload.description,
            body_part=(payload.body_part or ""),
            gender=(payload.gender or ""),
            video_url=str(payload.video_url),
            thumbnail_url=str(payload.thumbnail_url),
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
def update_video(
    video_id: int,
    payload: VideoUpdateRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

        if payload.body_part is not None:
            video.body_part = payload.body_part
        if payload.gender is not None:
            video.gender = payload.gender
        if payload.title is not None:
            video.title = payload.title
        if payload.description is not None:
            video.description = payload.description
        if payload.video_url is not None:
            video.video_url = str(payload.video_url)
        if payload.thumbnail_url is not None:
            video.thumbnail_url = str(payload.thumbnail_url)

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
