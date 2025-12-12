from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.constants import DEFAULT_ALL_GENDER_LABEL
from app.models.question import Question, UserAnswer
from app.models.user import User


def _pending_required_query(db: Session, user: User):
    query = db.query(Question).filter(
        Question.is_active == True,
        Question.is_required == True,
    )

    normalized_gender = (user.gender or "").strip().lower()
    if normalized_gender:
        query = query.filter(
            or_(
                Question.gender.is_(None),
                func.lower(Question.gender) == func.lower(DEFAULT_ALL_GENDER_LABEL),
                func.lower(Question.gender) == normalized_gender,
            )
        )
    else:
        query = query.filter(
            or_(
                Question.gender.is_(None),
                func.lower(Question.gender) == func.lower(DEFAULT_ALL_GENDER_LABEL),
            )
        )

    query = query.outerjoin(
        UserAnswer,
        (UserAnswer.question_id == Question.id) & (UserAnswer.user_id == user.id),
    ).filter(UserAnswer.id.is_(None))

    return query


def get_pending_required_questions(db: Session, user: User):
    return (
        _pending_required_query(db, user)
        .order_by(Question.created_at.asc())
        .all()
    )


def count_pending_required_questions(db: Session, user: User) -> int:
    return _pending_required_query(db, user).count()
