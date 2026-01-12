from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.health import HealthStep
from app.models.user import User
from app.schemas.health import StepCreate, StepResponse
from app.services.auth_middleware import get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/health", tags=["Health"], dependencies=[Depends(get_current_user)])


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")


def _step_payload(step: HealthStep | None) -> dict:
    if not step:
        return StepResponse(date=date.today().isoformat(), steps=0, source=None).model_dump()
    return StepResponse(
        date=step.step_date.isoformat(),
        steps=step.steps,
        source=step.source,
    ).model_dump()


@router.post("/steps")
def upsert_steps(
    body: StepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        step_date = _parse_date(body.date)
        step = (
            db.query(HealthStep)
            .filter(HealthStep.user_id == current_user.id, HealthStep.step_date == step_date)
            .first()
        )
        if step:
            step.steps = body.steps
            step.source = body.source
        else:
            step = HealthStep(
                user_id=current_user.id,
                step_date=step_date,
                steps=body.steps,
                source=body.source,
            )
            db.add(step)
        db.commit()
        db.refresh(step)
        return create_response(
            message="Steps saved successfully",
            data=_step_payload(step),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/steps/today")
def get_today_steps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        today = date.today()
        step = (
            db.query(HealthStep)
            .filter(HealthStep.user_id == current_user.id, HealthStep.step_date == today)
            .first()
        )
        return create_response(
            message="Today's steps fetched successfully",
            data=_step_payload(step),
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/steps/history")
def get_step_history(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        steps = (
            db.query(HealthStep)
            .filter(
                HealthStep.user_id == current_user.id,
                HealthStep.step_date >= start_date,
                HealthStep.step_date <= end_date,
            )
            .all()
        )
        step_map = {step.step_date: step for step in steps}
        entries = []
        iter_date = end_date
        while iter_date >= start_date:
            step = step_map.get(iter_date)
            payload = StepResponse(
                date=iter_date.isoformat(),
                steps=step.steps if step else 0,
                source=step.source if step else None,
            ).model_dump()
            entries.append(payload)
            iter_date -= timedelta(days=1)
        return create_response(
            message="Step history fetched successfully",
            data={
                "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "entries": entries,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
