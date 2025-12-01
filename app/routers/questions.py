import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import Question
from app.models.user import User
from app.schemas.question import (
    QuestionCreate,
    QuestionResponse,
    QuestionTypeEnum,
    QuestionUpdate,
)
from app.services.auth_middleware import get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/questions", tags=["Questions"])


def _normalize_units(units: list[str] | None) -> list[str] | None:
    if units is None:
        return None
    cleaned = [unit.strip() for unit in units if isinstance(unit, str) and unit.strip()]
    return cleaned or None


def _serialize_units(units: list[str] | None) -> str | None:
    if not units:
        return None
    return json.dumps(units)


def _deserialize_units(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(unit) for unit in parsed if str(unit).strip()]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _question_payload(question: Question) -> dict:
    measurement_units = _deserialize_units(question.measurement_unit)
    return QuestionResponse(
        id=question.id,
        prompt=question.prompt,
        answer=question.answer,
        gender=question.gender,
        question_type=question.question_type,
        measurement_units=measurement_units,
        created_at=question.created_at,
        updated_at=question.updated_at,
    ).model_dump()


def _enforce_measurement_unit(question_type: str, measurement_units: list[str] | None):
    if question_type in {QuestionTypeEnum.weight.value, QuestionTypeEnum.height.value} and not measurement_units:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="measurement_units is required for weight or height questions",
        )


@router.post("")
def create_question(
    body: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        measurement_units = _normalize_units(body.measurement_units)
        _enforce_measurement_unit(body.question_type.value, measurement_units)

        question = Question(
            prompt=body.prompt,
            answer=body.answer,
            gender=body.gender,
            question_type=body.question_type.value,
            measurement_unit=_serialize_units(measurement_units),
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        payload = _question_payload(question)
        return create_response(
            message="Question created successfully",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("")
def list_questions(
    question_type: QuestionTypeEnum | None = Query(None),
    gender: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Question).order_by(Question.created_at.desc())
        if question_type:
            query = query.filter(Question.question_type == question_type.value)
        if gender:
            query = query.filter(Question.gender == gender)

        questions = query.all()
        payload = [_question_payload(question) for question in questions]
        return create_response(
            message="Questions fetched successfully",
            data={"count": len(payload), "questions": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        payload = _question_payload(question)
        return create_response(
            message="Question fetched successfully",
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.put("/{question_id}")
def update_question(
    question_id: int,
    body: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        update_data = body.model_dump(exclude_unset=True)
        question_type_update = update_data.get("question_type")
        if isinstance(question_type_update, QuestionTypeEnum):
            question_type_value = question_type_update.value
        else:
            question_type_value = question_type_update

        existing_units = _deserialize_units(question.measurement_unit)
        units_provided = "measurement_units" in update_data
        if units_provided:
            updated_units = _normalize_units(update_data.get("measurement_units"))
            final_units = updated_units
        else:
            final_units = existing_units

        final_question_type = question_type_value or question.question_type
        _enforce_measurement_unit(final_question_type, final_units)

        for field, value in update_data.items():
            if field == "measurement_units":
                continue
            if isinstance(value, QuestionTypeEnum):
                value = value.value
            setattr(question, field, value)

        if units_provided:
            question.measurement_unit = _serialize_units(final_units)

        db.commit()
        db.refresh(question)
        payload = _question_payload(question)
        return create_response(
            message="Question updated successfully",
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        db.delete(question)
        db.commit()

        return create_response(
            message="Question deleted successfully",
            data={"deleted": True, "question_id": question_id},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
