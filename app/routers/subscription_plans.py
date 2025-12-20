from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.subscription_plan import SubscriptionPlan
from app.schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate
from app.services.auth_middleware import get_current_admin, get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/plans", tags=["Plans"])


def _plan_payload(plan: SubscriptionPlan) -> dict:
    payload = SubscriptionPlanResponse.model_validate(plan).model_dump()
    payload["name"] = payload.get("name") or _plan_name(payload["duration_months"])
    payload["description"] = payload.get("description") or _plan_description(payload["duration_months"])
    payload["monthly_equivalent"] = payload["monthly_equivalent"] or round(
        payload["discounted_price"] / payload["duration_months"], 2
    )
    if not payload.get("billing_term"):
        payload["billing_term"] = _billing_term(payload["duration_months"])
    return payload


def _billing_term(duration_months: int) -> str:
    if duration_months == 1:
        return "Billed monthly"
    if duration_months == 3:
        return "Billed quarterly"
    if duration_months == 12:
        return "Billed yearly"
    return f"Billed every {duration_months} months"


def _plan_name(duration_months: int) -> str:
    return f"{duration_months}-month plan"


def _plan_description(duration_months: int) -> str:
    if duration_months == 1:
        return "Monthly plan"
    if duration_months == 3:
        return "Quarterly plan"
    if duration_months == 12:
        return "Annual plan"
    return f"{duration_months} month plan"


@router.get("")
def list_active_plans(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    del user
    try:
        plans = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.is_active == True)
            .order_by(SubscriptionPlan.duration_months.asc())
            .all()
        )
        return create_response(
            message="Active plans fetched",
            data={"count": len(plans), "plans": [_plan_payload(plan) for plan in plans]},
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/admin")
def list_all_plans(
    include_inactive: bool = Query(
        False,
        description="Include inactive plans in the response alongside active entries.",
    ),
    status_filter: Optional[Literal["active", "inactive", "all"]] = Query(
        None,
        alias="status",
        description="Filter plans by status; defaults to active unless include_inactive is true.",
    ),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(SubscriptionPlan)

        effective_status = status_filter
        if effective_status is None:
            effective_status = "all" if include_inactive else "active"

        if effective_status == "active":
            query = query.filter(SubscriptionPlan.is_active == True)
        elif effective_status == "inactive":
            query = query.filter(SubscriptionPlan.is_active == False)
        elif not include_inactive:
            # Backwards compatibility for legacy callers expecting active plans only.
            query = query.filter(SubscriptionPlan.is_active == True)

        plans = query.order_by(SubscriptionPlan.created_at.desc()).all()
        return create_response(
            message="Plans fetched",
            data={"count": len(plans), "plans": [_plan_payload(plan) for plan in plans]},
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("/admin", status_code=status.HTTP_201_CREATED)
def create_plan(
    body: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        data = body.model_dump()
        duration = data["duration_months"]
        if not data.get("monthly_equivalent"):
            data["monthly_equivalent"] = data["discounted_price"] / duration
        if not data.get("billing_term"):
            data["billing_term"] = _billing_term(duration)
        if not data.get("name"):
            data["name"] = _plan_name(duration)
        if not data.get("description"):
            data["description"] = _plan_description(duration)
        plan = SubscriptionPlan(**data)
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return create_response(
            message="Plan created",
            data=_plan_payload(plan),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/admin/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    del admin
    try:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        return create_response(message="Plan fetched", data=_plan_payload(plan))
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.put("/admin/{plan_id}")
def update_plan(
    plan_id: int,
    body: SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        update_data = body.model_dump(exclude_unset=True)
        if "duration_months" in update_data or "discounted_price" in update_data:
            duration = update_data.get("duration_months", plan.duration_months)
            price = update_data.get("discounted_price", plan.discounted_price)
            update_data.setdefault("monthly_equivalent", price / duration)
            update_data.setdefault("billing_term", _billing_term(duration))
            if "name" not in update_data:
                update_data.setdefault("name", _plan_name(duration))
            if "description" not in update_data:
                update_data.setdefault("description", _plan_description(duration))
        for field, value in update_data.items():
            setattr(plan, field, value)
        db.commit()
        db.refresh(plan)
        return create_response(message="Plan updated", data=_plan_payload(plan))
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.delete("/admin/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    del admin
    try:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        db.delete(plan)
        db.commit()
        return create_response(message="Plan deleted", data=None, status_code=status.HTTP_200_OK)
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)
