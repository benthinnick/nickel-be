import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.infrastructure.database.session import create_engine
from app.infrastructure.database.tables import Base
from app.main import create_app


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("KAFKA_ENABLED", "false")
    monkeypatch.setenv("REDIS_URL", "fakeredis://")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "memory://")
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", "nickel-api")
    monkeypatch.setenv("KEYCLOAK_TEST_SECRET", "test-oidc-secret-at-least-32-bytes")
    monkeypatch.setenv("ELASTICSEARCH_URL", "memory://")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
async def session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    async with session_factory() as session:
        yield session
        await session.commit()
