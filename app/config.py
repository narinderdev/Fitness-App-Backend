import os
from dotenv import load_dotenv
from fastapi.security import HTTPBearer

load_dotenv()

class Settings:
    PROJECT_NAME = "Fitness Backend"

    DATABASE_URL = os.getenv("DATABASE_URL")

    JWT_SECRET = os.getenv("JWT_SECRET")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Bearer token extractor for Swagger & middleware
    bearer_scheme = HTTPBearer()

settings = Settings()
