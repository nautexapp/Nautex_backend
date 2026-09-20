from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Silenciar logs excesivos del SDK de Azure
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, get_engine, init_db
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
    from app.config import get_settings
    s = get_settings()
    return {
        "azure_tenant_id": s.azure_tenant_id,
        "azure_client_id": s.azure_client_id,
        "entra_client_id": s.entra_client_id,
        "base_dir": str(s.model_config.get("env_file")),
    }

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
