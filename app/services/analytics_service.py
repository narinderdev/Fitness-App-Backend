import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.health import HealthStep
from app.models.nutrition import FoodLog
from app.models.user import User  # noqa: F401 - ensure mapper registered
from app.models.water import WaterLog

logger = logging.getLogger(__name__)


def _date_range(days: int) -> tuple[date, date]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def _water_totals(db: Session, user_id: int, start_date: date, end_date: date) -> dict[date, int]:
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    rows = (
        db.query(func.date(WaterLog.logged_at), func.coalesce(func.sum(WaterLog.amount_ml), 0))
        .filter(
            WaterLog.user_id == user_id,
            WaterLog.logged_at >= start_dt,
            WaterLog.logged_at <= end_dt,
        )
        .group_by(func.date(WaterLog.logged_at))
        .all()
    )
    return {row[0]: int(row[1]) for row in rows}


def _step_totals(db: Session, user_id: int, start_date: date, end_date: date) -> dict[date, int]:
    rows = (
        db.query(HealthStep.step_date, func.coalesce(HealthStep.steps, 0))
        .filter(
            HealthStep.user_id == user_id,
            HealthStep.step_date >= start_date,
            HealthStep.step_date <= end_date,
        )
        .all()
    )
    return {row[0]: int(row[1] or 0) for row in rows}


def _nutrition_totals(db: Session, user_id: int, start_date: date, end_date: date) -> dict[date, dict]:
    rows = (
        db.query(
            FoodLog.consumed_date,
            func.coalesce(func.sum(FoodLog.calories), 0.0),
            func.coalesce(func.sum(FoodLog.protein), 0.0),
            func.coalesce(func.sum(FoodLog.carbs), 0.0),
            func.coalesce(func.sum(FoodLog.fat), 0.0),
        )
        .filter(
            FoodLog.user_id == user_id,
            FoodLog.consumed_date >= start_date,
            FoodLog.consumed_date <= end_date,
        )
        .group_by(FoodLog.consumed_date)
        .all()
    )
    return {
        row[0]: {
            "calories": float(row[1] or 0),
            "protein": float(row[2] or 0),
            "carbs": float(row[3] or 0),
            "fat": float(row[4] or 0),
        }
        for row in rows
    }


def get_user_analytics(db: Session, user_id: int, days: int = 7) -> dict:
    logger.info("Building analytics for user_id=%s days=%s", user_id, days)
    start_date, end_date = _date_range(days)
    logger.debug("Analytics window %s -> %s", start_date, end_date)
    water_map = _water_totals(db, user_id, start_date, end_date)
    logger.debug("Water totals: %s", water_map)
    step_map = _step_totals(db, user_id, start_date, end_date)
    logger.debug("Step totals: %s", step_map)
    nutrition_map = _nutrition_totals(db, user_id, start_date, end_date)
    logger.debug("Nutrition totals: %s", nutrition_map)

    entries: list[dict] = []
    cumulative = {"water_ml": 0, "steps": 0, "calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    cursor = end_date
    while cursor >= start_date:
        nutrition = nutrition_map.get(cursor, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0})
        entry = {
            "date": cursor.isoformat(),
            "water_ml": water_map.get(cursor, 0),
            "steps": step_map.get(cursor, 0),
            "calories": round(nutrition["calories"], 2),
            "protein": round(nutrition["protein"], 2),
            "carbs": round(nutrition["carbs"], 2),
            "fat": round(nutrition["fat"], 2),
        }
        entries.append(entry)
        cumulative["water_ml"] += entry["water_ml"]
        cumulative["steps"] += entry["steps"]
        cumulative["calories"] += entry["calories"]
        cumulative["protein"] += entry["protein"]
        cumulative["carbs"] += entry["carbs"]
        cumulative["fat"] += entry["fat"]
        cursor -= timedelta(days=1)

    days_count = max(len(entries), 1)
    averages = {key: round(value / days_count, 2) for key, value in cumulative.items()}
    today_entry = entries[0] if entries else None

    logger.info("Analytics ready for user_id=%s entries=%s", user_id, len(entries))
    return {
        "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "entries": entries,
        "totals": {key: (round(value, 2) if isinstance(value, float) else value) for key, value in cumulative.items()},
        "averages": averages,
        "today": today_entry,
    }
