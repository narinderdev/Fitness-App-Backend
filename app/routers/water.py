import logging
from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.water import WaterLog, DeviceToken
from app.models.user import User
from app.schemas.water import WaterLogCreate, WaterSummaryResponse, DeviceTokenCreate, NotificationRequest
from app.services.auth_middleware import get_current_user
from app.services.firebase_service import send_push_notification
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/water", tags=["Water"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


@router.post("/logs")
def log_water(
    body: WaterLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info(
            "User %s logging water entry: amount_ml=%s, logged_at=%s",
            current_user.id,
            body.amount_ml,
            body.logged_at,
        )
        logged_at = datetime.fromisoformat(body.logged_at) if body.logged_at else datetime.utcnow()
        log = WaterLog(user_id=current_user.id, amount_ml=body.amount_ml, logged_at=logged_at)
        db.add(log)
        db.commit()
        db.refresh(log)
        logger.info("User %s logged water entry id=%s at %s", current_user.id, log.id, log.logged_at.isoformat())
        return create_response(
            message="Water logged successfully",
            data={"id": log.id, "amount_ml": log.amount_ml, "logged_at": log.logged_at.isoformat()},
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/today")
def today_water(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info("Fetching today's water total for user %s", current_user.id)
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        total = (
            db.query(WaterLog)
            .filter(WaterLog.user_id == current_user.id, WaterLog.logged_at >= start, WaterLog.logged_at <= end)
            .with_entities(WaterLog.amount_ml)
            .all()
        )
        amount = sum(value for (value,) in total)
        logger.info("User %s consumed %s mL of water today", current_user.id, amount)
        return create_response(
            message="Today's water intake fetched",
            data={"date": today.isoformat(), "amount_ml": amount},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/history")
def water_history(
    days: int = Query(7, ge=1, le=31),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info("Fetching %s-day water history for user %s", days, current_user.id)
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        logs = (
            db.query(WaterLog)
            .filter(
                WaterLog.user_id == current_user.id,
                WaterLog.logged_at >= datetime.combine(start_date, datetime.min.time()),
                WaterLog.logged_at <= datetime.combine(end_date, datetime.max.time()),
            )
            .all()
        )
        totals = {}
        for log in logs:
            key = log.logged_at.date()
            totals.setdefault(key, 0)
            totals[key] += log.amount_ml

        entries = []
        cursor = end_date
        while cursor >= start_date:
            entries.append({"date": cursor.isoformat(), "amount_ml": totals.get(cursor, 0)})
            cursor -= timedelta(days=1)

        logger.info(
            "Water history ready for user %s covering %s to %s",
            current_user.id,
            start_date.isoformat(),
            end_date.isoformat(),
        )
        return create_response(
            message="Water history fetched",
            data={"range": {"start": start_date.isoformat(), "end": end_date.isoformat()}, "entries": entries},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/tokens")
def register_device_token(
    body: DeviceTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info(
            "User %s registering device token %s for platform %s",
            current_user.id,
            body.token,
            body.platform,
        )
        token_record = db.query(DeviceToken).filter(DeviceToken.token == body.token).first()
        if token_record:
            token_record.user_id = current_user.id
            token_record.platform = body.platform
        else:
            token_record = DeviceToken(user_id=current_user.id, token=body.token, platform=body.platform)
            db.add(token_record)
        db.commit()
        logger.info(
            "Device token %s registered for user %s (platform=%s)",
            token_record.token,
            current_user.id,
            token_record.platform,
        )
        return create_response(
            message="Device token registered",
            data={"token": token_record.token, "platform": token_record.platform},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.delete("/tokens")
def unregister_device_token(
    token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info("User %s removing device token %s", current_user.id, token)
        token_record = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id == current_user.id, DeviceToken.token == token)
            .first()
        )
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device token not found",
            )
        db.delete(token_record)
        db.commit()
        logger.info("Device token %s removed for user %s", token, current_user.id)
        return create_response(
            message="Device token removed",
            data={"token": token},
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.post("/reminder")
def send_water_reminder(
    body: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info("User %s requested water reminder: title=%s", current_user.id, body.title)
        tokens = [token.token for token in current_user.device_tokens]
        if not tokens:
            logger.warning("User %s has no device tokens for reminders", current_user.id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No device tokens registered")
        result = send_push_notification(tokens, body.title, body.body, data={"type": "water_reminder"})
        logger.info(
            "Water reminder sent for user %s to %s devices",
            current_user.id,
            len(tokens),
        )
        invalid_tokens = result.get("invalid_tokens") or []
        if invalid_tokens:
            logger.info("Cleaning up %s invalid tokens for user %s", len(invalid_tokens), current_user.id)
            (
                db.query(DeviceToken)
                .filter(DeviceToken.token.in_(invalid_tokens))
                .delete(synchronize_session=False)
            )
            db.commit()
        return create_response(
            message="Reminder sent",
            data=result,
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except Exception as exc:
        return handle_exception(exc)
