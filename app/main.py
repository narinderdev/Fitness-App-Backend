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
    programs,
    profile,
    questions,
    subscription_plans,
    products,
    users,
    exercise_library,
    videos,
    water,
    weight,
    progress_photos,
    legal_links,
    usda,
)
from app.utils.response import create_response, handle_exception
from app.utils.db_migrations import (
    ensure_program_price_column,
    drop_food_category_slug_and_sort,
    ensure_user_flag_columns,
    ensure_user_health_ack_column,
    ensure_user_daily_goal_column,
    ensure_user_daily_water_goal_column,
    ensure_food_item_usda_columns,
    ensure_legal_links_subscription_column,
    migrate_app_settings_to_legal_links,
    ensure_video_duration_column,
    drop_products_key_column,
    ensure_product_link_column,
)
from seed import run_seed
from app.services.water_reminder_service import reminder_scheduler
from app.services.progress_reminder_service import progress_reminder_scheduler

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
    ensure_program_price_column(engine)
    drop_food_category_slug_and_sort(engine)
    ensure_user_flag_columns(engine)
    ensure_user_health_ack_column(engine)
    ensure_user_daily_goal_column(engine)
    ensure_user_daily_water_goal_column(engine)
    ensure_food_item_usda_columns(engine)
    migrate_app_settings_to_legal_links(engine)
    ensure_legal_links_subscription_column(engine)
    ensure_video_duration_column(engine)
    drop_products_key_column(engine)
    ensure_product_link_column(engine)
    run_seed()
    await reminder_scheduler.start()
    await progress_reminder_scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    await reminder_scheduler.stop()
    await progress_reminder_scheduler.stop()

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
app.include_router(nutrition.admin_router)
app.include_router(water.router)
app.include_router(weight.router)
app.include_router(analytics.router)
app.include_router(subscription_plans.router)
app.include_router(products.router)
app.include_router(products.admin_router)
app.include_router(programs.router)
app.include_router(exercise_library.router)
app.include_router(progress_photos.router)
app.include_router(legal_links.router)
app.include_router(usda.router)

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


@app.get("/api-info")
def api_info():
    try:
        return create_response(
            message="API information",
            data={
                "service": settings.PROJECT_NAME,
                "version": "1.0.0",
                "docs_url": "/docs",
                "openapi_url": "/openapi.json",
                "health_check": "/health",
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
