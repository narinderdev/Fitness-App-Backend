from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import AnswerOption, Question, UserAnswer, UserAnswerOption
from app.models.user import User
from app.schemas.answers import UserAnswerCreate, UserAnswerResponse, UserAnswerOptionResponse
from app.services.auth_middleware import get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/answers", tags=["Answers"])


def _answer_payload(answer: UserAnswer) -> dict:
    option_payloads = [
        UserAnswerOptionResponse(
            id=selection.id,
            option_id=selection.option_id,
            option_text=selection.option.option_text if selection.option else "",
            value=selection.option.value if selection.option else None,
            created_at=selection.created_at,
        )
        for selection in answer.selected_options
    ]

    return UserAnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        question=answer.question.question if answer.question else "",
        question_description=answer.question.description if answer.question else None,
        answer_type=answer.question.answer_type if answer.question else "",
        answer_text=answer.answer_text,
        created_at=answer.created_at,
        options=option_payloads,
    ).model_dump()


@router.post("")
def submit_answer(
    body: UserAnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        question = db.query(Question).filter(Question.id == body.question_id, Question.is_active == True).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        answer = (
            db.query(UserAnswer)
            .filter(
                UserAnswer.user_id == current_user.id,
                UserAnswer.question_id == question.id,
            )
            .first()
        )
        if answer:
            answer.answer_text = body.answer_text
            db.query(UserAnswerOption).filter(UserAnswerOption.user_answer_id == answer.id).delete()
        else:
            answer = UserAnswer(
                user_id=current_user.id,
                question_id=question.id,
                answer_text=body.answer_text,
            )
            db.add(answer)
            db.flush()

        if body.options:
            option_ids = [opt.option_id for opt in body.options]
            valid_options = (
                db.query(AnswerOption)
                .filter(
                    AnswerOption.id.in_(option_ids),
                    AnswerOption.question_id == question.id,
                    AnswerOption.is_active == True,
                )
                .all()
            )
            valid_map = {option.id: option for option in valid_options}

            for option_id in option_ids:
                option = valid_map.get(option_id)
                if not option:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid option id {option_id} for question {question.id}",
                    )
                db.add(UserAnswerOption(user_answer_id=answer.id, option_id=option_id))

        db.commit()
        db.refresh(answer)
        payload = _answer_payload(answer)
        return create_response(
            message="Answer submitted successfully",
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("")
def list_user_answers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        answers = (
            db.query(UserAnswer)
            .filter(UserAnswer.user_id == current_user.id)
            .order_by(UserAnswer.created_at.desc())
            .all()
        )
        payload = [_answer_payload(answer) for answer in answers]
        return create_response(
            message="Answers fetched successfully",
            data={"count": len(payload), "answers": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
