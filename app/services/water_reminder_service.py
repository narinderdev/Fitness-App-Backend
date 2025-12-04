import asyncio
import logging

from app.config import settings
from app.database import SessionLocal
from app.models.water import DeviceToken
from app.services.firebase_service import send_push_notification

logger = logging.getLogger(__name__)


class WaterReminderScheduler:
    """Background scheduler that periodically pushes water reminders."""

    def __init__(self, interval_minutes: int, enabled: bool = True):
        self.interval_seconds = max(interval_minutes, 1) * 60
        self.enabled = enabled
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Automatic water reminders disabled by configuration.")
            return
        if self._task and not self._task.done():
            return
        logger.info("Starting automatic water reminders every %s minutes", self.interval_seconds / 60)
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
            await self._send_reminder()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def _send_reminder(self) -> None:
        tokens = self._fetch_tokens()
        if not tokens:
            logger.debug("Skipping automatic reminder; no device tokens registered.")
            return
        logger.info("Sending automatic water reminder to %s devices", len(tokens))
        try:
            result = send_push_notification(
                tokens,
                settings.WATER_REMINDER_TITLE,
                settings.WATER_REMINDER_BODY,
                data={"type": "water_reminder", "source": "auto"},
            )
            logger.info(
                "Automatic reminder finished: success=%s failure=%s",
                result.get("success"),
                result.get("failure"),
            )
        except Exception:
            logger.exception("Failed to send automatic water reminder")

    @staticmethod
    def _fetch_tokens() -> list[str]:
        session = SessionLocal()
        try:
            token_rows = session.query(DeviceToken.token).all()
            return [token for (token,) in token_rows]
        finally:
            session.close()


reminder_scheduler = WaterReminderScheduler(
    interval_minutes=settings.WATER_REMINDER_INTERVAL_MINUTES,
    enabled=settings.WATER_REMINDER_AUTO_ENABLED,
)
