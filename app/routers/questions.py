from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import AnswerOption, Question
from app.models.user import User
from app.schemas.question import (
    AnswerOptionResponse,
    AnswerOptionUpdate,
    AnswerTypeEnum,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)
from app.services.auth_middleware import get_current_user, get_current_admin
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/questions", tags=["Questions"])

CHOICE_TYPES = {AnswerTypeEnum.single_choice.value, AnswerTypeEnum.multi_choice.value}
DEFAULT_ALL_GENDER_LABEL = "Both"


def _question_payload(question: Question) -> dict:
    options = sorted(question.options, key=lambda opt: opt.id or 0)
    option_payloads = [
        AnswerOptionResponse(
            id=option.id,
            question_id=option.question_id,
            option_text=option.option_text,
            value=option.value,
            is_active=option.is_active,
            created_at=option.created_at,
            updated_at=option.updated_at,
        )
        for option in options
    ]

    return QuestionResponse(
        id=question.id,
        question=question.question,
        description=question.description,
        answer_type=question.answer_type,
        gender=question.gender,
        is_required=question.is_required,
        is_active=question.is_active,
        created_at=question.created_at,
        updated_at=question.updated_at,
        options=option_payloads,
    ).model_dump()


def _ensure_choice_has_options(answer_type: str, options_source: list) -> None:
    if answer_type in CHOICE_TYPES and not options_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer options are required for single or multi choice questions",
        )


def _sync_options(
    db: Session,
    question: Question,
    options_payload: list[AnswerOptionUpdate | dict],
) -> None:
    existing = {option.id: option for option in question.options if option.id is not None}
    seen_ids: set[int] = set()

    for payload in options_payload:
        data = payload if isinstance(payload, dict) else payload.model_dump()
        option_id = data.get("id")
        option_text = data.get("option_text")
        value = data.get("value")
        is_active = data.get("is_active")

        if not option_text or not option_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="option_text is required for each answer option",
            )

        if option_id:
            option = existing.get(option_id)
            if not option:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Answer option {option_id} not found",
                )
            option.option_text = option_text
            option.value = value
            option.is_active = is_active if is_active is not None else option.is_active
            seen_ids.add(option_id)
        else:
            is_active_value = True if is_active is None else is_active
            new_option = AnswerOption(
                question_id=question.id,
                option_text=option_text,
                value=value,
                is_active=is_active_value,
            )
            db.add(new_option)

    for option in list(question.options):
        if option.id and option.id not in seen_ids and options_payload:
            db.delete(option)

    db.flush()
    db.refresh(question)


@router.post("")
def create_question(
    body: QuestionCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        gender_value = body.gender
        if gender_value and gender_value.lower() == "all":
            gender_value = DEFAULT_ALL_GENDER_LABEL

        question = Question(
            question=body.question,
            description=body.description,
            answer_type=body.answer_type.value,
            gender=gender_value,
            is_required=body.is_required,
            is_active=body.is_active,
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        options_payload = body.options or []
        _ensure_choice_has_options(question.answer_type, options_payload)
        if options_payload:
            _sync_options(db, question, options_payload)
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
    answer_type: AnswerTypeEnum | None = Query(None),
    gender: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Question).order_by(Question.created_at.desc())
        if answer_type:
            query = query.filter(Question.answer_type == answer_type.value)
        if gender:
            if gender.lower() == "all":
                query = query.filter(Question.gender == DEFAULT_ALL_GENDER_LABEL)
            else:
                query = query.filter(Question.gender == gender)
        if is_active is not None:
            query = query.filter(Question.is_active == is_active)

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
    current_admin=Depends(get_current_admin),
):
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        update_data = body.model_dump(exclude_unset=True)
        options_payload = update_data.pop("options", None)

        for field, value in update_data.items():
            if field == "answer_type" and isinstance(value, AnswerTypeEnum):
                value = value.value
            if field == "gender" and isinstance(value, str) and value.lower() == "all":
                value = DEFAULT_ALL_GENDER_LABEL
            setattr(question, field, value)

        if options_payload is not None:
            _sync_options(db, question, options_payload)

        _ensure_choice_has_options(question.answer_type, question.options)
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
    current_admin=Depends(get_current_admin),
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
