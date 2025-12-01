from fastapi import FastAPI, status
from app.database import Base, engine
from app.routers import auth, profile
from seed import run_seed
from app.utils.response import create_response, handle_exception

app = FastAPI()

# Auto create tables
Base.metadata.create_all(bind=engine)

# Seed default user on startup
@app.on_event("startup")
def startup_event():
    run_seed()

# Add routes
app.include_router(auth.router)
app.include_router(profile.router)

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
