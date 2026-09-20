from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings

settings = get_settings()

def _get_database_url(settings: Settings) -> str:
    return settings.database_url

engine = None

AsyncSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
)

def init_db():
    global engine
    if engine is None:
        engine = create_async_engine(
            _get_database_url(settings),
            echo=False,
            pool_pre_ping=True,
        )
        AsyncSessionLocal.configure(bind=engine)

def get_engine():
    if engine is None:
        init_db()
    return engine

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
