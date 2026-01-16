import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.water import DeviceToken
from app.services.auth_middleware import get_current_user
from app.services.firebase_service import send_push_notification
from app.services.referral_service import ensure_referral_code
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/referrals", tags=["Referrals"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


@router.get("/me")
def referral_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        ensure_referral_code(db, user)
        db.commit()
        referral_count = (
            db.query(User).filter(User.referred_by_id == user.id).count()
        )
        return create_response(
            message="Referral info fetched",
            data={
                "referral_code": user.referral_code,
                "referrals": referral_count,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/notify")
def send_coupon_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        referrals_count = db.query(User).filter(User.referred_by_id == user.id).count()
        if referrals_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No referrals yet",
            )
        tokens = [token.token for token in user.device_tokens]
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No device tokens registered",
            )

        coupon_code = settings.REFERRAL_COUPON_CODE
        title = settings.REFERRAL_NOTIFICATION_TITLE
        body = settings.REFERRAL_NOTIFICATION_BODY.format(code=coupon_code)
        result = send_push_notification(
            tokens,
            title,
            body,
            data={"type": "referral_reward", "coupon_code": coupon_code},
        )
        invalid_tokens = result.get("invalid_tokens") or []
        if invalid_tokens:
            (
                db.query(DeviceToken)
                .filter(DeviceToken.token.in_(invalid_tokens))
                .delete(synchronize_session=False)
            )
            db.commit()

        logger.info(
            "Referral coupon notification sent to user %s (referrals=%s)",
            user.id,
            referrals_count,
        )
        return create_response(
            message="Coupon notification sent",
            data={"coupon_code": coupon_code, "referrals": referrals_count},
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except Exception as exc:
        return handle_exception(exc)
