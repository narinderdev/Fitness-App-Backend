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
    FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE")

    bearer_scheme = HTTPBearer()
    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]


settings = Settings()
