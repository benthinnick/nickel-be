from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.infrastructure.database.tables import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(database_url: str) -> AsyncEngine:
    kwargs: dict = {}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    return create_async_engine(database_url, **kwargs)


def configure_database(settings: Settings) -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    if _engine is not None:
        return _session_factory  # type: ignore[return-value]
    _engine = create_engine(settings.database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database is not configured")
    return _session_factory


async def create_tables() -> None:
    if _engine is None:
        raise RuntimeError("Database is not configured")
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
