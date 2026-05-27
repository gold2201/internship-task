from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_active_user, get_current_user
from app.core.settings import settings
from app.db.base import Base
from app.db.session import db_manager
from app.main import app

engine = create_async_engine(settings.test_database_url, echo=False)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session")
def event_loop():
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    admin_engine = create_async_engine(settings.database_url, echo=False, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": settings.TEST_DB},
        )
        if not result.fetchone():
            await conn.execute(text(f"CREATE DATABASE {settings.TEST_DB}"))

    await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database():
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


async def override_get_async_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def override_get_current_user():
    async with SessionLocal() as session:
        from app.repositories.user_repository import UserRepository

        repo = UserRepository(session)
        user = await repo.get_by_email("tester@test.com")
        return user


async def override_get_active_user():
    return await override_get_current_user()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[db_manager.get_async_session] = override_get_async_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_active_user] = override_get_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
