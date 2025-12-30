import asyncio
import logging
from collections import defaultdict
from datetime import date

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
from app.services.measurement_utils import parse_numeric_value, weight_kg_from_answer

logger = logging.getLogger(__name__)

CALORIES_PER_STEP = 0.04
DEFAULT_BASE_CALORIES = 1200
MAX_BASE_CALORIES = 4000


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
    if current_weight is None:
        current_weight = _current_weight_from_answers(answers)
    goal_weight = _goal_weight_from_answers(answers)
    timeframe_days = _goal_timeframe_days_from_answers(answers)
    if current_weight is None or goal_weight is None or not timeframe_days:
        return None

    maintenance = current_weight * 30
    delta = goal_weight - current_weight
    if abs(delta) < 0.01 or timeframe_days <= 0:
        target = maintenance
    else:
        daily_delta = (abs(delta) * 7700) / timeframe_days
        target = maintenance + (daily_delta if delta > 0 else -daily_delta)
    target_calories = round(max(DEFAULT_BASE_CALORIES, min(MAX_BASE_CALORIES, target)))

    burned_calories = _todays_burned_calories(session, user_id)
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


def _todays_consumed_calories(session, user_id: int) -> float:
    today = date.today()
    logs = (
        session.query(FoodLog)
        .filter(FoodLog.user_id == user_id, FoodLog.consumed_date == today)
        .all()
    )
    return sum(log.calories or 0 for log in logs)


def _todays_burned_calories(session, user_id: int) -> int:
    today = date.today()
    step = (
        session.query(HealthStep)
        .filter(HealthStep.user_id == user_id, HealthStep.step_date == today)
        .first()
    )
    steps = step.steps if step else 0
    return round(steps * CALORIES_PER_STEP)


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
