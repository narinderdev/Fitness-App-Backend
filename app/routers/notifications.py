import logging
from typing import Iterable, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.water import DeviceToken
from app.schemas.notifications import AdminNotificationRequest
from app.services.auth_middleware import get_current_admin
from app.services.firebase_service import send_push_notification
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = logging.getLogger(__name__)


def _chunk_tokens(tokens: List[str], size: int = 500) -> Iterable[List[str]]:
    for idx in range(0, len(tokens), size):
        yield tokens[idx : idx + size]


def _collect_tokens(db: Session, body: AdminNotificationRequest) -> List[str]:
    audience = body.audience.strip().lower()
    query = db.query(User).filter(User.is_admin == False)

    if audience == "all":
        pass
    elif audience == "active":
        query = query.filter(User.is_active == True)
    elif audience == "inactive":
        query = query.filter(User.is_active == False)
    elif audience == "purchased_plan":
        query = query.filter(User.purchased_plan == True)
    elif audience == "pilates_board":
        query = query.filter(User.has_pilates_board == True)
    elif audience == "user_ids":
        if not body.user_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User IDs required")
        query = query.filter(User.id.in_(body.user_ids))
    elif audience == "emails":
        if not body.emails:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emails required")
        normalized_emails = [email.lower().strip() for email in body.emails]
        query = query.filter(User.email.in_(normalized_emails))
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audience option")

    users = query.all()
    tokens: List[str] = []
    for user in users:
        for token in user.device_tokens:
            tokens.append(token.token)
    return list(dict.fromkeys(tokens))


@router.post("/admin/send")
def admin_send_notification(
    body: AdminNotificationRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        tokens = _collect_tokens(db, body)
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No device tokens found for the selected audience",
            )

        total_success = 0
        total_failure = 0
        invalid_tokens: List[str] = []
        for chunk in _chunk_tokens(tokens):
            result = send_push_notification(chunk, body.title, body.body, data=body.data)
            total_success += result.get("success", 0)
            total_failure += result.get("failure", 0)
            invalid_tokens.extend(result.get("invalid_tokens") or [])

        if invalid_tokens:
            (
                db.query(DeviceToken)
                .filter(DeviceToken.token.in_(invalid_tokens))
                .delete(synchronize_session=False)
            )
            db.commit()

        logger.info(
            "Admin notification sent success=%s failure=%s invalid=%s",
            total_success,
            total_failure,
            len(invalid_tokens),
        )
        return create_response(
            message="Notification sent",
            data={
                "success": total_success,
                "failure": total_failure,
                "invalid_tokens": invalid_tokens,
            },
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except Exception as exc:
        return handle_exception(exc)
