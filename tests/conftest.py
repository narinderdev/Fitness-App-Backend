import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure predictable environment variables for tests before importing the app.
BASE_DIR = Path(__file__).resolve().parents[1]
TEST_DB_PATH = BASE_DIR / "test.db"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("WATER_REMINDER_AUTO_ENABLED", "false")

import app.main as main  # noqa: E402  (import after env vars are set)


@pytest.fixture()
def client(monkeypatch):
    """Provide a TestClient with startup tasks patched out for isolation."""
    monkeypatch.setattr(main, "run_seed", lambda: None)

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr(main.reminder_scheduler, "start", _noop_async)
    monkeypatch.setattr(main.reminder_scheduler, "stop", _noop_async)

    with TestClient(main.app) as test_client:
        yield test_client
