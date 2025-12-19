from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.program import Program, ProgramDay
from app.models.video import Video
from app.schemas.program import (
    ProgramCreate,
    ProgramDayCreate,
    ProgramDayResponse,
    ProgramDayUpdate,
    ProgramDayPreview,
    ProgramDetailResponse,
    ProgramResponse,
    ProgramTimeline,
    ProgramUpdate,
    ProgramVisibility,
    ProgramVideoSnippet,
)
from app.services.auth_middleware import get_current_admin, get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/programs", tags=["Programs"])
PREVIEW_LIMIT = 7


def _access_enum(value: str | None) -> ProgramVisibility:
    if value and value in ProgramVisibility._value2member_map_:
        return ProgramVisibility(value)
    return ProgramVisibility.free


def _normalize_slug(slug: str) -> str:
    return slug.strip().lower().replace(" ", "-")


def _program_payload(program: Program, preview_days: Iterable[ProgramDay] | None = None) -> dict:
    access = _access_enum(program.access_level)
    preview = [
        ProgramDayPreview(
            day_number=day.day_number,
            title=day.title,
            focus=day.focus,
            is_rest_day=day.is_rest_day,
        ).model_dump()
        for day in (preview_days or [])
    ]
    payload = ProgramResponse(
        id=program.id,
        slug=program.slug,
        title=program.title,
        subtitle=program.subtitle,
        description=program.description,
        duration_days=program.duration_days,
        workouts_per_week=program.workouts_per_week,
        rest_days_per_week=program.rest_days_per_week,
        level=program.level,
        access_level=access,
        cta_label=program.cta_label,
        hero_image_url=program.hero_image_url,
        cover_image_url=program.cover_image_url,
        is_featured=program.is_featured,
        is_active=program.is_active,
        created_at=program.created_at,
        updated_at=program.updated_at,
        days_count=program.duration_days,
        requires_payment=access == ProgramVisibility.paid,
        preview_days=preview,
    ).model_dump()
    return payload


def _day_payload(day: ProgramDay) -> dict:
    video_snippet = None
    if day.video_id:
        video_snippet = ProgramVideoSnippet(
            id=day.video_id,
            title=getattr(day.video, "title", None),
            thumbnail_url=getattr(day.video, "thumbnail_url", None),
            video_url=getattr(day.video, "video_url", None),
        )
    payload = ProgramDayResponse(
        id=day.id,
        program_id=day.program_id,
        day_number=day.day_number,
        title=day.title,
        focus=day.focus,
        description=day.description,
        is_rest_day=day.is_rest_day,
        workout_summary=day.workout_summary,
        duration_minutes=day.duration_minutes,
        video_id=day.video_id,
        tips=day.tips,
        created_at=day.created_at,
        updated_at=day.updated_at,
        video=video_snippet,
    ).model_dump()
    return payload


def _timeline_payload(days: List[ProgramDay]) -> dict:
    rest_days = sum(1 for day in days if day.is_rest_day)
    workouts = max(len(days) - rest_days, 0)
    return ProgramTimeline(
        total_days=len(days),
        workouts=workouts,
        rest_days=rest_days,
    ).model_dump()


def _fetch_preview_days(db: Session, program_ids: List[int]) -> Dict[int, List[ProgramDay]]:
    if not program_ids:
        return {}
    rows = (
        db.query(ProgramDay)
        .filter(ProgramDay.program_id.in_(program_ids))
        .order_by(ProgramDay.program_id.asc(), ProgramDay.day_number.asc())
        .all()
    )
    mapping: Dict[int, List[ProgramDay]] = defaultdict(list)
    for day in rows:
        bucket = mapping[day.program_id]
        if len(bucket) < PREVIEW_LIMIT:
            bucket.append(day)
    return mapping


def _program_by_identifier(db: Session, identifier: str) -> Program:
    query = db.query(Program)
    program: Optional[Program] = None
    if identifier.isdigit():
        program = query.filter(Program.id == int(identifier)).first()
    if not program:
        program = query.filter(Program.slug == identifier).first()
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program


def _ensure_unique_day_number(db: Session, program_id: int, day_number: int, exclude_id: int | None = None):
    query = db.query(ProgramDay).filter(
        ProgramDay.program_id == program_id,
        ProgramDay.day_number == day_number,
    )
    if exclude_id:
        query = query.filter(ProgramDay.id != exclude_id)
    exists = db.query(query.exists()).scalar()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Day {day_number} already exists for this program.",
        )


def _validate_video(db: Session, video_id: Optional[int]) -> Optional[Video]:
    if not video_id:
        return None
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


@router.get("")
def list_programs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    del user
    try:
        programs = (
            db.query(Program)
            .filter(Program.is_active == True)
            .order_by(Program.is_featured.desc(), Program.created_at.asc())
            .all()
        )
        previews = _fetch_preview_days(db, [program.id for program in programs])
        payload = [
            _program_payload(program, previews.get(program.id, []))
            for program in programs
        ]
        return create_response(
            message="Programs fetched",
            data={"count": len(payload), "programs": payload},
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/admin")
def admin_list_programs(
    include_inactive: bool = Query(True, description="Include inactive programs."),
    access_filter: ProgramVisibility | None = Query(
        None, alias="access", description="Filter by access level (free or paid)."
    ),
    include_days: bool = Query(
        False, description="Include the full day schedule for each program."
    ),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        query = db.query(Program)
        if not include_inactive:
            query = query.filter(Program.is_active == True)
        if access_filter:
            query = query.filter(Program.access_level == access_filter.value)
        programs = query.order_by(Program.created_at.desc()).all()
        previews = _fetch_preview_days(db, [program.id for program in programs])
        items = []
        for program in programs:
            payload = _program_payload(program, previews.get(program.id, []))
            if include_days:
                days = (
                    db.query(ProgramDay)
                    .options(joinedload(ProgramDay.video))
                    .filter(ProgramDay.program_id == program.id)
                    .order_by(ProgramDay.day_number.asc())
                    .all()
                )
                payload["days"] = [_day_payload(day) for day in days]
            items.append(payload)
        return create_response(
            message="Programs fetched",
            data={"count": len(items), "programs": items},
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/admin", status_code=status.HTTP_201_CREATED)
def create_program(
    body: ProgramCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        slug = _normalize_slug(body.slug)
        existing = db.query(Program).filter(Program.slug == slug).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use.")
        program = Program(
            slug=slug,
            title=body.title.strip(),
            subtitle=body.subtitle,
            description=body.description,
            duration_days=body.duration_days,
            workouts_per_week=body.workouts_per_week,
            rest_days_per_week=body.rest_days_per_week,
            level=body.level,
            access_level=body.access_level.value,
            cta_label=body.cta_label or ("Unlock Program" if body.access_level == ProgramVisibility.paid else "Start for Free"),
            hero_image_url=body.hero_image_url,
            cover_image_url=body.cover_image_url,
            is_active=body.is_active,
            is_featured=body.is_featured,
        )
        db.add(program)
        db.commit()
        db.refresh(program)
        payload = _program_payload(program, [])
        return create_response(
            message="Program created",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.put("/admin/{program_identifier}")
def update_program(
    program_identifier: str,
    body: ProgramUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        program = _program_by_identifier(db, program_identifier)
        update_data = body.model_dump(exclude_unset=True)
        if "slug" in update_data and update_data["slug"]:
            slug = _normalize_slug(update_data["slug"])
            duplicate = (
                db.query(Program)
                .filter(Program.slug == slug, Program.id != program.id)
                .first()
            )
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use.")
            update_data["slug"] = slug
        for field, value in update_data.items():
            if hasattr(program, field):
                setattr(program, field, value)
        db.commit()
        db.refresh(program)
        payload = _program_payload(program, [])
        return create_response(message="Program updated", data=payload)
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.delete("/admin/{program_identifier}")
def delete_program(program_identifier: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    del admin
    try:
        program = _program_by_identifier(db, program_identifier)
        db.delete(program)
        db.commit()
        return create_response(message="Program deleted", data={"deleted": True})
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.post("/admin/{program_identifier}/days", status_code=status.HTTP_201_CREATED)
def create_program_day(
    program_identifier: str,
    body: ProgramDayCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        program = _program_by_identifier(db, program_identifier)
        _ensure_unique_day_number(db, program.id, body.day_number)
        _validate_video(db, body.video_id)
        day = ProgramDay(
            program_id=program.id,
            day_number=body.day_number,
            title=body.title.strip(),
            focus=body.focus,
            description=body.description,
            is_rest_day=body.is_rest_day,
            workout_summary=body.workout_summary,
            duration_minutes=body.duration_minutes,
            video_id=body.video_id,
            tips=body.tips,
        )
        db.add(day)
        db.commit()
        db.refresh(day)
        payload = _day_payload(day)
        return create_response(
            message="Program day created",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.put("/admin/{program_identifier}/days/{day_id}")
def update_program_day(
    program_identifier: str,
    day_id: int,
    body: ProgramDayUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        program = _program_by_identifier(db, program_identifier)
        day = (
            db.query(ProgramDay)
            .filter(ProgramDay.id == day_id, ProgramDay.program_id == program.id)
            .options(joinedload(ProgramDay.video))
            .first()
        )
        if not day:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program day not found")
        update_data = body.model_dump(exclude_unset=True)
        if "day_number" in update_data and update_data["day_number"]:
            _ensure_unique_day_number(db, program.id, update_data["day_number"], exclude_id=day.id)
        if "video_id" in update_data:
            _validate_video(db, update_data["video_id"])
        for field, value in update_data.items():
            setattr(day, field, value)
        db.commit()
        db.refresh(day)
        payload = _day_payload(day)
        return create_response(message="Program day updated", data=payload)
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.delete("/admin/{program_identifier}/days/{day_id}")
def delete_program_day(
    program_identifier: str,
    day_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        program = _program_by_identifier(db, program_identifier)
        day = (
            db.query(ProgramDay)
            .filter(ProgramDay.id == day_id, ProgramDay.program_id == program.id)
            .first()
        )
        if not day:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program day not found")
        db.delete(day)
        db.commit()
        return create_response(message="Program day deleted", data={"deleted": True})
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.get("/{program_identifier}")
def get_program_detail(program_identifier: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    del user
    try:
        program = _program_by_identifier(db, program_identifier)
        days = (
            db.query(ProgramDay)
            .options(joinedload(ProgramDay.video))
            .filter(ProgramDay.program_id == program.id)
            .order_by(ProgramDay.day_number.asc())
            .all()
        )
        preview = days[:PREVIEW_LIMIT]
        payload = ProgramDetailResponse(
            program=_program_payload(program, preview),
            days=[_day_payload(day) for day in days],
            timeline=_timeline_payload(days),
        ).model_dump()
        return create_response(message="Program fetched", data=payload)
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)
