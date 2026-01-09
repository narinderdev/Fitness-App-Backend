from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.question import AnswerOption, Question, UserAnswer, UserAnswerOption
from app.models.user import User
from app.models.weight import WeightLog
from app.services.measurement_utils import weight_kg_from_answer


def add_weight_log_from_answer(db: Session, user: User, answer: UserAnswer) -> Optional[WeightLog]:
    weight_kg = weight_kg_from_answer(answer)
    if weight_kg is None or weight_kg <= 0:
        return None

    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    existing_log = (
        db.query(WeightLog)
        .filter(
            WeightLog.user_id == user.id,
            WeightLog.logged_at >= start_of_day,
            WeightLog.logged_at <= end_of_day,
        )
        .first()
    )
    if existing_log:
        existing_log.weight_kg = weight_kg
        existing_log.logged_at = answer.created_at or datetime.utcnow()
        return existing_log

    log = WeightLog(
        user_id=user.id,
        weight_kg=weight_kg,
        logged_at=answer.created_at or datetime.utcnow(),
    )
    db.add(log)
    return log


def sync_weight_answer_from_log(db: Session, user: User, weight_kg: float) -> Optional[UserAnswer]:
    question = (
        db.query(Question)
        .filter(Question.answer_type == "weight", Question.is_active == True)
        .order_by(Question.id.asc())
        .first()
    )
    if not question:
        return None

    answer = (
        db.query(UserAnswer)
        .filter(UserAnswer.user_id == user.id, UserAnswer.question_id == question.id)
        .order_by(UserAnswer.created_at.desc())
        .first()
    )
    now = datetime.utcnow()
    formatted_value = f"{weight_kg:.1f} kg"
    if answer:
        answer.answer_text = formatted_value
        answer.created_at = now
        db.query(UserAnswerOption).filter(UserAnswerOption.user_answer_id == answer.id).delete()
    else:
        answer = UserAnswer(
            user_id=user.id,
            question_id=question.id,
            answer_text=formatted_value,
            created_at=now,
        )
        db.add(answer)
        db.flush()

    kg_option = _resolve_kg_option(question)
    if kg_option:
        db.add(UserAnswerOption(user_answer_id=answer.id, option_id=kg_option.id))
    return answer


def resolve_starting_weight(db: Session, user: User) -> tuple[float, datetime] | None:
    earliest_log = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.asc())
        .first()
    )
    if earliest_log:
        return earliest_log.weight_kg, earliest_log.logged_at

    answers = (
        db.query(UserAnswer)
        .join(Question, UserAnswer.question_id == Question.id)
        .filter(UserAnswer.user_id == user.id, Question.is_active == True)
        .order_by(UserAnswer.created_at.asc())
        .all()
    )
    current_answer = _find_weight_answer(answers, include=["current weight"])
    if current_answer:
        parsed = weight_kg_from_answer(current_answer)
        if parsed is not None and parsed > 0:
            return parsed, current_answer.created_at

    fallback_answer = _find_weight_answer(
        answers,
        include=[],
        exclude=["goal weight", "target weight"],
    )
    if fallback_answer:
        parsed = weight_kg_from_answer(fallback_answer)
        if parsed is not None and parsed > 0:
            return parsed, fallback_answer.created_at
    return None


def _find_weight_answer(
    answers: list[UserAnswer],
    include: list[str],
    exclude: list[str] | None = None,
) -> Optional[UserAnswer]:
    for answer in answers:
        question = answer.question
        if not question:
            continue
        question_text = question.question.lower()
        if include and not any(keyword in question_text for keyword in include):
            continue
        if exclude and any(keyword in question_text for keyword in exclude):
            continue
        if question.answer_type.lower() != "weight":
            continue
        return answer
    return None


def _resolve_kg_option(question: Question) -> Optional[AnswerOption]:
    kg_aliases = {"kg", "kgs", "kilogram", "kilograms"}
    for option in question.options or []:
        for source in (option.value, option.option_text):
            if not source:
                continue
            normalized = source.strip().lower()
            if normalized in kg_aliases or normalized.startswith("kg"):
                return option
    return None
