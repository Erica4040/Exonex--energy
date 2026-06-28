"""
PlastiQ — Plastic Waste Detection & Pyrolysis Yield Intelligence Platform
FastAPI application entrypoint.

Run locally:
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Then visit http://localhost:8000/docs for interactive API documentation.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.routers import auth, dashboard, facilities, reports, waste
from app.seed.demo_data import seed_if_empty

# Import models package so every ORM model registers on Base.metadata
# before create_all runs.
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    if settings.SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()

    yield
    # (no shutdown cleanup required for SQLite/local dev)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Computer-vision-driven plastic waste detection, pyrolysis suitability "
        "scoring, oil/gas/carbon-black yield prediction, revenue forecasting, "
        "risk detection, and business-intelligence reporting for recycling "
        "centers, landfills, municipal waste facilities, and plastic-to-fuel plants."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(facilities.router, prefix=settings.API_V1_PREFIX)
app.include_router(waste.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
