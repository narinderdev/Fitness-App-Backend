import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models.health import HealthStep
from app.models.nutrition import FoodLog
from app.models.question import Question, UserAnswer, UserAnswerOption
from app.models.user import User
from app.models.water import DeviceToken
from app.models.weight import WeightLog
from app.services.firebase_service import send_push_notification
from app.services.measurement_utils import (
    convert_height_to_m,
    parse_numeric_value,
    resolve_height_unit,
    weight_kg_from_answer,
)

logger = logging.getLogger(__name__)

CALORIES_PER_STEP = 0.04
REFERENCE_WEIGHT_KG = 70
DEFAULT_BASE_CALORIES = 1200
MAX_BASE_CALORIES = 4000
ACTIVITY_MULTIPLIER = 1.2
BMR_MALE_OFFSET = 5
BMR_FEMALE_OFFSET = -161


class ProgressReminderScheduler:
    """Background scheduler that periodically pushes goal-calorie progress updates."""

    def __init__(self, interval_minutes: int, enabled: bool = True):
        self.interval_seconds = max(interval_minutes, 1) * 60
        self.enabled = enabled
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Progress updates disabled by configuration.")
            return
        if self._task and not self._task.done():
            return
        logger.info("Starting progress reminders every %s minutes", self.interval_seconds / 60)
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self._send_reminders()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def _send_reminders(self) -> None:
        session = SessionLocal()
        try:
            token_rows = (
                session.query(DeviceToken)
                .join(User, User.id == DeviceToken.user_id)
                .filter(User.is_active == True)
                .all()
            )
            tokens_by_user: dict[int, list[str]] = defaultdict(list)
            for token in token_rows:
                tokens_by_user[token.user_id].append(token.token)

            if not tokens_by_user:
                logger.debug("Skipping progress reminders; no device tokens registered.")
                return

            invalid_tokens: list[str] = []
            for user_id, tokens in tokens_by_user.items():
                reminder = _build_user_reminder(session, user_id)
                if reminder is None:
                    continue
                title, body, payload = reminder
                try:
                    result = send_push_notification(tokens, title, body, data=payload)
                    invalid_tokens.extend(result.get("invalid_tokens") or [])
                except Exception:
                    logger.exception("Failed to send progress reminder for user %s", user_id)

            if invalid_tokens:
                logger.info("Progress reminders removing %s invalid tokens", len(invalid_tokens))
                session.query(DeviceToken).filter(DeviceToken.token.in_(invalid_tokens)).delete(synchronize_session=False)
                session.commit()
        finally:
            session.close()


def _build_user_reminder(session, user_id: int) -> tuple[str, str, dict[str, str]] | None:
    target_payload = _calculate_target_calories(session, user_id)
    if not target_payload:
        return None
    target_calories, burned_calories = target_payload
    consumed_calories = _todays_consumed_calories(session, user_id)
    daily_allowance = target_calories + burned_calories
    remaining = round(daily_allowance - consumed_calories)
    if remaining <= 0:
        return None

    title = settings.PROGRESS_REMINDER_TITLE
    body = _format_progress_body(remaining, daily_allowance)
    payload = {
        "type": "progress_update",
        "remaining_calories": str(remaining),
        "target_calories": str(daily_allowance),
    }
    return title, body, payload


def _calculate_target_calories(session, user_id: int) -> tuple[int, int] | None:
    current_weight = _latest_weight_kg(session, user_id)
    answers = _fetch_answers(session, user_id)
    user = session.query(User).filter(User.id == user_id).first()
    if current_weight is None:
        current_weight = _current_weight_from_answers(answers)
    goal_weight = _goal_weight_from_answers(answers)
    timeframe_days = _goal_timeframe_days_from_answers(answers)
    if current_weight is None or goal_weight is None or not timeframe_days:
        return None

    height_cm = _height_cm_from_answers(answers)
    age_years = _age_years_from_answers(answers)
    if age_years is None and user and user.dob:
        age_years = _age_from_raw_date(user.dob)
    gender = _gender_from_answers(answers) or (user.gender if user else None)
    maintenance = _estimate_maintenance_calories(
        weight_kg=current_weight,
        height_cm=height_cm,
        age_years=age_years,
        gender=gender,
    )
    delta = goal_weight - current_weight
    if abs(delta) < 0.01 or timeframe_days <= 0:
        target = maintenance
    else:
        daily_delta = (abs(delta) * 7700) / timeframe_days
        target = maintenance + (daily_delta if delta > 0 else -daily_delta)
    target_calories = round(max(DEFAULT_BASE_CALORIES, target))

    burned_calories = _todays_burned_calories(session, user_id, current_weight)
    return target_calories, burned_calories


def _latest_weight_kg(session, user_id: int) -> float | None:
    log = (
        session.query(WeightLog)
        .filter(WeightLog.user_id == user_id)
        .order_by(WeightLog.logged_at.desc())
        .first()
    )
    return log.weight_kg if log else None


def _fetch_answers(session, user_id: int) -> list[UserAnswer]:
    return (
        session.query(UserAnswer)
        .join(Question, Question.id == UserAnswer.question_id)
        .options(
            joinedload(UserAnswer.question),
            joinedload(UserAnswer.selected_options).joinedload(UserAnswerOption.option),
        )
        .filter(UserAnswer.user_id == user_id)
        .order_by(UserAnswer.created_at.desc())
        .all()
    )


def _find_answer_by_keywords(
    answers: list[UserAnswer],
    include: list[str],
    exclude: list[str] | None = None,
) -> UserAnswer | None:
    for answer in answers:
        question_text = (answer.question.question if answer.question else "").lower()
        if not any(keyword in question_text for keyword in include):
            continue
        if exclude and any(keyword in question_text for keyword in exclude):
            continue
        return answer
    return None


def _goal_weight_from_answers(answers: list[UserAnswer]) -> float | None:
    answer = _find_answer_by_keywords(answers, include=["goal weight", "target weight"])
    if not answer:
        return None
    return weight_kg_from_answer(answer)


def _current_weight_from_answers(answers: list[UserAnswer]) -> float | None:
    answer = _find_answer_by_keywords(answers, include=["current weight"])
    if answer:
        parsed = weight_kg_from_answer(answer)
        if parsed is not None:
            return parsed
    weight_answers = [
        entry
        for entry in answers
        if (entry.question.answer_type if entry.question else "").lower() == "weight"
        and not _question_contains(entry.question.question if entry.question else "", ["goal weight", "target weight"])
    ]
    for entry in weight_answers:
        parsed = weight_kg_from_answer(entry)
        if parsed is not None:
            return parsed
    return None


def _goal_timeframe_days_from_answers(answers: list[UserAnswer]) -> int | None:
    answer = _find_answer_by_keywords(
        answers,
        include=["week", "month", "time", "timeframe", "reach"],
    )
    if not answer:
        return None
    value = parse_numeric_value(answer.answer_text)
    if value is None or value <= 0:
        return None
    unit = _resolve_unit(answer)
    if unit and "month" in unit:
        return max(int(round(value * 30)), 1)
    if unit and "day" in unit:
        return max(int(round(value)), 1)
    return max(int(round(value * 7)), 1)


def _resolve_unit(answer: UserAnswer) -> str | None:
    for selection in answer.selected_options or []:
        option = selection.option
        if not option:
            continue
        for source in (option.value, option.option_text):
            if source and source.strip():
                return source.strip().lower()
    text = (answer.answer_text or "").lower()
    for token in ("lb", "kg", "month", "week", "day"):
        if token in text:
            return token
    return None


def _question_contains(question: str, keywords: list[str]) -> bool:
    normalized = question.lower()
    return any(keyword in normalized for keyword in keywords)


def _height_cm_from_answers(answers: list[UserAnswer]) -> float | None:
    for entry in answers:
        question = entry.question.question if entry.question else ""
        answer_type = (entry.question.answer_type if entry.question else "").lower()
        if answer_type != "height" and "height" not in question.lower():
            continue
        value = parse_numeric_value(entry.answer_text)
        if value is None:
            continue
        unit = resolve_height_unit(entry)
        height_m = convert_height_to_m(value, unit)
        if height_m is None:
            continue
        return height_m * 100
    return None


def _age_years_from_answers(answers: list[UserAnswer]) -> int | None:
    answer = _find_answer_by_keywords(
        answers,
        include=["date of birth", "dob", "birth"],
    )
    raw = answer.answer_text if answer else None
    return _age_from_raw_date(raw)


def _age_from_raw_date(raw: str | None) -> int | None:
    if not raw or not raw.strip():
        return None
    parsed = None
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        try:
            parsed = datetime.fromisoformat(raw.strip()[:10])
        except ValueError:
            return None
    return _age_from_date(parsed.date())


def _age_from_date(dob: date) -> int | None:
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age if age >= 0 else None


def _gender_from_answers(answers: list[UserAnswer]) -> str | None:
    answer = _find_answer_by_keywords(answers, include=["gender"])
    if not answer:
        return None
    raw = None
    for selection in answer.selected_options or []:
        option = selection.option
        if not option:
            continue
        for source in (option.value, option.option_text):
            if source and source.strip():
                raw = source.strip()
                break
        if raw:
            break
    raw = raw or answer.answer_text
    if not raw:
        return None
    normalized = raw.strip().lower()
    if "female" in normalized:
        return "female"
    if "male" in normalized:
        return "male"
    return None


def _estimate_maintenance_calories(
    *,
    weight_kg: float,
    height_cm: float | None,
    age_years: int | None,
    gender: str | None,
) -> float:
    if height_cm is not None and age_years is not None:
        base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years)
        offset = _gender_bmr_offset(gender)
        bmr = base + offset
        if bmr > 0:
            return bmr * ACTIVITY_MULTIPLIER
    return weight_kg * 30


def _gender_bmr_offset(gender: str | None) -> float:
    normalized = (gender or "").strip().lower()
    if normalized == "male":
        return BMR_MALE_OFFSET
    if normalized == "female":
        return BMR_FEMALE_OFFSET
    return 0


def _todays_consumed_calories(session, user_id: int) -> float:
    today = date.today()
    logs = (
        session.query(FoodLog)
        .filter(FoodLog.user_id == user_id, FoodLog.consumed_date == today)
        .all()
    )
    return sum(log.calories or 0 for log in logs)


def _todays_burned_calories(session, user_id: int, weight_kg: float | None) -> int:
    today = date.today()
    step = (
        session.query(HealthStep)
        .filter(HealthStep.user_id == user_id, HealthStep.step_date == today)
        .first()
    )
    steps = step.steps if step else 0
    weight = max(weight_kg or REFERENCE_WEIGHT_KG, 1)
    return round(steps * CALORIES_PER_STEP * (weight / REFERENCE_WEIGHT_KG))


def _format_progress_body(remaining: int, target: int) -> str:
    template = settings.PROGRESS_REMINDER_BODY or ""
    if template:
        try:
            return template.format(remaining=remaining, target=target)
        except Exception:
            return template
    return f"You have {remaining} calories left to reach today's goal."


progress_reminder_scheduler = ProgressReminderScheduler(
    interval_minutes=settings.PROGRESS_REMINDER_INTERVAL_MINUTES,
    enabled=settings.PROGRESS_REMINDER_AUTO_ENABLED,
)
