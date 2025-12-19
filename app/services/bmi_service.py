from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.question import Question, UserAnswer, UserAnswerOption
from app.models.user import User
from app.services.measurement_utils import (
    convert_height_to_m,
    convert_weight_to_kg,
    parse_numeric_value,
    resolve_height_unit,
    resolve_weight_unit,
)


def recalculate_user_bmi(
    db: Session,
    user: User,
    weight_kg_override: float | None = None,
) -> Optional[dict]:
    """
    Attempts to update the given user's BMI based on their latest height and weight answers.
    Returns a payload describing the BMI when both values are available, otherwise None.
    """
    weight_answer = None if weight_kg_override is not None else _get_latest_answer(db, user.id, "weight")
    height_answer = _get_latest_answer(db, user.id, "height")

    if height_answer is None:
        user.bmi_value = None
        user.bmi_category = None
        return None

    if weight_kg_override is None and weight_answer is None:
        user.bmi_value = None
        user.bmi_category = None
        return None

    height_value = parse_numeric_value(height_answer.answer_text)
    if height_value is None:
        user.bmi_value = None
        user.bmi_category = None
        return None

    if weight_kg_override is None:
        weight_value = parse_numeric_value(weight_answer.answer_text)
        if weight_value is None:
            user.bmi_value = None
            user.bmi_category = None
            return None
        weight_unit = resolve_weight_unit(weight_answer)
        weight_kg = convert_weight_to_kg(weight_value, weight_unit)
    else:
        weight_kg = weight_kg_override

    height_unit = resolve_height_unit(height_answer)
    height_m = convert_height_to_m(height_value, height_unit)
    if weight_kg is None or height_m is None or height_m <= 0:
        user.bmi_value = None
        user.bmi_category = None
        return None

    bmi = round(weight_kg / (height_m * height_m), 1)
    category = _resolve_bmi_category(bmi)
    user.bmi_value = bmi
    user.bmi_category = category
    return {"value": bmi, "category": category}


def _get_latest_answer(db: Session, user_id: int, answer_type: str) -> UserAnswer | None:
    return (
        db.query(UserAnswer)
        .join(Question, UserAnswer.question_id == Question.id)
        .options(
            joinedload(UserAnswer.selected_options).joinedload(UserAnswerOption.option),
            joinedload(UserAnswer.question),
        )
        .filter(UserAnswer.user_id == user_id, Question.answer_type == answer_type)
        .order_by(UserAnswer.created_at.desc())
        .first()
    )


def _resolve_bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"
