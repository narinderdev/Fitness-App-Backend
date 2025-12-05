from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.video import Video


def get_dashboard_metrics(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    inactive_users = total_users - active_users

    total_videos = db.query(func.count(Video.id)).scalar() or 0
    videos_by_body_part = (
        db.query(Video.body_part, func.count(Video.id))
        .group_by(Video.body_part)
        .all()
    )
    videos_by_body_part = [
        {"category": body_part, "count": count}
        for body_part, count in videos_by_body_part
    ]

    videos_by_gender = (
        db.query(Video.gender, func.count(Video.id))
        .group_by(Video.gender)
        .all()
    )
    videos_by_gender = [
        {"gender": gender, "count": count}
        for gender, count in videos_by_gender
    ]

    videos_by_category_gender = (
        db.query(Video.body_part, Video.gender, func.count(Video.id))
        .group_by(Video.body_part, Video.gender)
        .all()
    )
    videos_by_category_gender = [
        {"category": body_part, "gender": gender, "count": count}
        for body_part, gender, count in videos_by_category_gender
    ]

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
        },
        "videos": {
            "total": total_videos,
            "by_category": videos_by_body_part,
            "by_gender": videos_by_gender,
            "by_category_gender": videos_by_category_gender,
        },
    }
