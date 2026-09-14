import socket
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app

settings = get_settings()


def _is_postgres_available() -> bool:
    try:
        s = socket.socket()
        s.settimeout(0.3)
        res = s.connect_ex(("127.0.0.1", 5432))
        s.close()
        return res == 0
    except Exception:
        return False


@pytest_asyncio.fixture(loop_scope="function")
async def client():
    """
    Async HTTP client fixture with database NullPool override.
    Ensures asyncpg connections are cleanly scoped to the current test event loop.
    """
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        future=True,
    )
    test_sessionmaker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _get_test_db():
        if not _is_postgres_available():
            pytest.skip("PostgreSQL database is not reachable on localhost:5432; start Docker/PostgreSQL to run DB integration tests.")
        async with test_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _get_test_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await test_engine.dispose()
