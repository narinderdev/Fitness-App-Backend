import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.analytics_service import get_user_analytics
from app.services.auth_middleware import get_current_admin, get_current_user
from app.services.dashboard_service import get_dashboard_metrics
from app.utils.response import create_response, handle_exception

router = APIRouter(tags=["Analytics"])
logger = logging.getLogger(__name__)


@router.get("/admin/users/analytics")
def admin_user_analytics(
    user_id: int = Query(..., gt=0),
    days: int = Query(7, ge=1, le=31),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        logger.info("Admin %s fetching analytics for user_id=%s days=%s", admin.id, user_id, days)
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive")
        analytics = get_user_analytics(db, user_id=user.id, days=days)
        return create_response(
            message="User analytics fetched",
            data={"user": {"id": user.id, "email": user.email}, "analytics": analytics},
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        logger.warning("Admin analytics request failed for user_id=%s", user_id, exc_info=True)
        raise
    except Exception as exc:
        logger.exception("Unexpected error building admin analytics for user_id=%s", user_id)
        return handle_exception(exc)


@router.get("/app/analytics")
def app_user_analytics(
    days: int = Query(7, ge=1, le=31),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info("User %s fetching analytics days=%s", current_user.id, days)
        analytics = get_user_analytics(db, user_id=current_user.id, days=days)
        return create_response(
            message="Analytics fetched",
            data=analytics,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.exception("Failed to build analytics for user %s", current_user.id)
        return handle_exception(exc)


@router.get("/admin/dashboard/metrics")
def admin_dashboard_metrics(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        logger.info("Admin %s requesting dashboard metrics", admin.id)
        metrics = get_dashboard_metrics(db)
        return create_response(
            message="Dashboard metrics fetched",
            data=metrics,
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        logger.exception("Failed to build dashboard metrics for admin %s", admin.id)
        return handle_exception(Exception("Failed to build dashboard metrics"))
