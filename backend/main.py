"""FastAPI application entry point.

Composition only: request handling lives in `backend/routers/`, domain logic in
`backend.nutrition`, `backend.recommendation` and `backend.ml`.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    CORS_ORIGIN_REGEX,
    CORS_ORIGINS,
    ENVIRONMENT,
    validate_runtime_configuration,
)
from backend.database import SessionLocal, create_tables
from backend.food_data import seed_food_items
from backend.routers import auth, chat, foods, meals, profile, recommendations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start-up and shutdown work.

    Replaces the deprecated `@app.on_event("startup")` hook. Table creation is
    a convenience for a fresh local database; managed environments should run
    `alembic upgrade head` instead.
    """
    validate_runtime_configuration()
    create_tables()

    db = SessionLocal()
    try:
        inserted = seed_food_items(db)
        if inserted:
            logger.info("Seeded %s food items.", inserted)
    except FileNotFoundError as exc:
        logger.warning("Food catalogue not seeded: %s", exc)
    finally:
        db.close()

    yield


app = FastAPI(
    title="AI-Based Personalized Diet Recommendation & Nutrition Management API",
    description=(
        "Backend services for authentication, health profiles, meal tracking, "
        "ML-driven food recommendations and the nutrition coach."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for module in (auth, profile, meals, foods, recommendations, chat):
    app.include_router(module.router, prefix=API_PREFIX)


@app.get("/", tags=["meta"])
async def root():
    return {
        "message": "Welcome to the Nutrition AI API",
        "version": app.version,
        "environment": ENVIRONMENT,
        "docs_url": "/docs",
        "status": "healthy",
    }


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
