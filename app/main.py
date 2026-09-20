from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_engine, init_db
from app.routers import ai, courses, registration, users

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    if settings.debug:
        eng = get_engine()
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(registration.router, prefix=settings.api_prefix)
app.include_router(courses.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)


@app.get("/debug-settings")
def debug_settings():
    s = get_settings()
    return {
        "app_name": s.app_name,
        "debug": s.debug,
        "google_client_id_configured": bool(s.google_client_id),
        "r2_bucket_name": s.r2_bucket_name,
        "r2_configured": bool(s.r2_access_key_id or s.r2_public_url),
        "database_configured": bool(s.database_url),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
