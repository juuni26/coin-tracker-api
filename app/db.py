from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _build_engine(url: str) -> AsyncEngine:
    connect_args = {}
    # aiosqlite shares one connection across the app; check_same_thread=False
    # is required when used in async contexts that hop event-loop threads.
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(url, connect_args=connect_args, future=True)


engine: AsyncEngine = _build_engine(settings.DATABASE_URL)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
