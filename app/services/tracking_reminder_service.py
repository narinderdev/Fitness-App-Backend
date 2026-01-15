import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from app.config import settings
from app.database import SessionLocal
from app.models.progress_photo import ProgressPhoto
from app.models.user import User
from app.models.water import DeviceToken
from app.models.weight import WeightLog
from app.services.firebase_service import send_push_notification

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_DAYS = 7


class TrackingReminderScheduler:
    """Background scheduler for weekly weight/progress photo reminders."""

    def __init__(self, interval_minutes: int, enabled: bool = True):
        self.interval_seconds = max(interval_minutes, 1) * 60
        self.enabled = enabled
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Tracking reminders disabled by configuration.")
            return
        if self._task and not self._task.done():
            return
        logger.info("Starting tracking reminders every %s minutes", self.interval_seconds / 60)
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
                logger.debug("Skipping tracking reminders; no device tokens registered.")
                return

            invalid_tokens: list[str] = []
            now = datetime.utcnow()
            for user_id, tokens in tokens_by_user.items():
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    continue

                if _should_send_weight_reminder(session, user, now):
                    try:
                        result = send_push_notification(
                            tokens,
                            settings.WEIGHT_REMINDER_TITLE,
                            settings.WEIGHT_REMINDER_BODY,
                            data={"type": "weight_reminder", "source": "auto"},
                        )
                        invalid_tokens.extend(result.get("invalid_tokens") or [])
                        user.last_weight_reminder_at = now
                    except Exception:
                        logger.exception("Failed to send weight reminder for user %s", user_id)

                if _should_send_photo_reminder(session, user, now):
                    try:
                        result = send_push_notification(
                            tokens,
                            settings.PROGRESS_PHOTO_REMINDER_TITLE,
                            settings.PROGRESS_PHOTO_REMINDER_BODY,
                            data={"type": "progress_photo_reminder", "source": "auto"},
                        )
                        invalid_tokens.extend(result.get("invalid_tokens") or [])
                        user.last_progress_photo_reminder_at = now
                    except Exception:
                        logger.exception(
                            "Failed to send progress photo reminder for user %s",
                            user_id,
                        )

            if invalid_tokens:
                logger.info(
                    "Tracking reminders removing %s invalid tokens",
                    len(invalid_tokens),
                )
                session.query(DeviceToken).filter(DeviceToken.token.in_(invalid_tokens)).delete(
                    synchronize_session=False
                )
            session.commit()
        finally:
            session.close()


def _should_send_weight_reminder(session, user: User, now: datetime) -> bool:
    last_log = (
        session.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.desc())
        .first()
    )
    return _is_reminder_due(
        last_log.logged_at if last_log else None,
        user.last_weight_reminder_at,
        now,
    )


def _should_send_photo_reminder(session, user: User, now: datetime) -> bool:
    last_photo = (
        session.query(ProgressPhoto)
        .filter(ProgressPhoto.user_id == user.id)
        .order_by(ProgressPhoto.taken_at.desc())
        .first()
    )
    return _is_reminder_due(
        last_photo.taken_at if last_photo else None,
        user.last_progress_photo_reminder_at,
        now,
    )


def _is_reminder_due(
    last_log_at: datetime | None,
    last_reminder_at: datetime | None,
    now: datetime,
) -> bool:
    if last_log_at is None:
        return False
    days_since_log = (now.date() - last_log_at.date()).days
    if days_since_log < REMINDER_INTERVAL_DAYS:
        return False
    if last_reminder_at and last_reminder_at >= last_log_at:
        days_since_reminder = (now.date() - last_reminder_at.date()).days
        if days_since_reminder < REMINDER_INTERVAL_DAYS:
            return False
    return True


tracking_reminder_scheduler = TrackingReminderScheduler(
    interval_minutes=settings.TRACKING_REMINDER_INTERVAL_MINUTES,
    enabled=settings.TRACKING_REMINDER_AUTO_ENABLED,
)
