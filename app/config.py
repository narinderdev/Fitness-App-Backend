import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi.security import HTTPBearer

BASE_DIR = Path(__file__).resolve().parent.parent  # -> FITNESS_BACKEND

# Load .env explicitly from project root
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_NAME = "Fitness Backend"

    DATABASE_URL = os.getenv("DATABASE_URL")

    JWT_SECRET = os.getenv("JWT_SECRET")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
    FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE")
    WATER_REMINDER_INTERVAL_MINUTES = int(os.getenv("WATER_REMINDER_INTERVAL_MINUTES", 120))
    WATER_REMINDER_AUTO_ENABLED = os.getenv("WATER_REMINDER_AUTO_ENABLED", "true").lower() == "true"
    WATER_REMINDER_TITLE = os.getenv("WATER_REMINDER_TITLE", "Drink water")
    WATER_REMINDER_BODY = os.getenv("WATER_REMINDER_BODY", "Time to hydrate!")
    PROGRESS_REMINDER_INTERVAL_MINUTES = int(os.getenv("PROGRESS_REMINDER_INTERVAL_MINUTES", 1))
    PROGRESS_REMINDER_AUTO_ENABLED = os.getenv("PROGRESS_REMINDER_AUTO_ENABLED", "true").lower() == "true"
    PROGRESS_REMINDER_TITLE = os.getenv("PROGRESS_REMINDER_TITLE", "Progress update")
    PROGRESS_REMINDER_BODY = os.getenv(
        "PROGRESS_REMINDER_BODY",
        "You have {remaining} calories left to reach today's goal.",
    )

    bearer_scheme = HTTPBearer()
    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]


settings = Settings()
