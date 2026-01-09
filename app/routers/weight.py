import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.weight import WeightLog
from app.schemas.weight import WeightLogCreate
from app.services.auth_middleware import get_current_user
from app.services.bmi_service import recalculate_user_bmi
from app.services.weight_service import resolve_starting_weight, sync_weight_answer_from_log
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/weight", tags=["Weight"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


@router.post("/logs")
def log_weight(
    body: WeightLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logged_at = datetime.fromisoformat(body.logged_at) if body.logged_at else datetime.utcnow()
        today = date.today()
        existing = (
            db.query(WeightLog)
            .filter(
                WeightLog.user_id == current_user.id,
                WeightLog.logged_at >= datetime.combine(today, datetime.min.time()),
                WeightLog.logged_at <= datetime.combine(today, datetime.max.time()),
            )
            .first()
        )
        message = "Weight logged successfully"
        status_code = status.HTTP_201_CREATED
        if existing:
            existing.weight_kg = body.weight_kg
            existing.logged_at = logged_at
            log_entry = existing
            message = "Weight updated successfully"
            status_code = status.HTTP_200_OK
        else:
            log_entry = WeightLog(
                user_id=current_user.id,
                weight_kg=body.weight_kg,
                logged_at=logged_at,
            )
            db.add(log_entry)

        bmi_payload = recalculate_user_bmi(
            db,
            current_user,
            weight_kg_override=body.weight_kg,
        )
        sync_weight_answer_from_log(db, current_user, body.weight_kg)

        db.commit()
        db.refresh(log_entry)
        if not existing:
            logger.info(
                "User %s logged weight id=%s weight=%skg at %s",
                current_user.id,
                log_entry.id,
                log_entry.weight_kg,
                log_entry.logged_at.isoformat(),
            )

        return create_response(
            message=message,
            data={
                "weight_kg": log_entry.weight_kg,
                "logged_at": log_entry.logged_at.isoformat(),
                "bmi": bmi_payload,
            },
            status_code=status_code,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/latest")
def latest_weight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        log = (
            db.query(WeightLog)
            .filter(WeightLog.user_id == current_user.id)
            .order_by(WeightLog.logged_at.desc())
            .first()
        )
        if not log:
            return create_response(
                message="No weight logs found",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return create_response(
            message="Latest weight fetched",
            data={"weight_kg": log.weight_kg, "logged_at": log.logged_at.isoformat()},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/starting")
def starting_weight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        resolved = resolve_starting_weight(db, current_user)
        if not resolved:
            return create_response(
                message="No starting weight found",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        weight_kg, logged_at = resolved
        return create_response(
            message="Starting weight fetched",
            data={"weight_kg": weight_kg, "logged_at": logged_at.isoformat()},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/history")
def weight_history(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        logs = (
            db.query(WeightLog)
            .filter(
                WeightLog.user_id == current_user.id,
                WeightLog.logged_at >= datetime.combine(start_date, datetime.min.time()),
                WeightLog.logged_at <= datetime.combine(end_date, datetime.max.time()),
            )
            .order_by(WeightLog.logged_at.desc())
            .all()
        )
        by_day: dict[date, WeightLog] = {}
        for log in logs:
            key = log.logged_at.date()
            existing = by_day.get(key)
            if existing is None or log.logged_at > existing.logged_at:
                by_day[key] = log

        entries = [
            {
                "date": log.logged_at.date().isoformat(),
                "weight_kg": log.weight_kg,
                "logged_at": log.logged_at.isoformat(),
            }
            for log in sorted(by_day.values(), key=lambda item: item.logged_at)
        ]

        return create_response(
            message="Weight history fetched",
            data={
                "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "entries": entries,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
