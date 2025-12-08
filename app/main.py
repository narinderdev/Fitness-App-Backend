from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import (
    analytics,
    answers,
    auth,
    google_auth,
    health,
    nutrition,
    profile,
    questions,
    subscription_plans,
    users,
    videos,
    water,
)
from app.utils.response import create_response, handle_exception
from seed import run_seed
from app.services.water_reminder_service import reminder_scheduler

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Auto create tables
Base.metadata.create_all(bind=engine)

# CORS for SPA / API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed default user on startup
@app.on_event("startup")
async def startup_event():
    run_seed()
    await reminder_scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    await reminder_scheduler.stop()

# Add routes
app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(profile.router)
app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(videos.router)
app.include_router(users.router)
app.include_router(health.router)
app.include_router(nutrition.router)
app.include_router(water.router)
app.include_router(analytics.router)
app.include_router(subscription_plans.router)

# Serve uploaded assets
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def home():
    try:
        return create_response(
            message="Fitness API running",
            data={"service": "fitness-backend"},
            status_code=status.HTTP_200_OK
        )
    except Exception as exc:
        return handle_exception(exc)
