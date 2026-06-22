import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from sqlalchemy import delete
from app.main import app as prod_app
from app.database import Base
from app.db_depends import get_async_db
from app.models import Product


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # отдельная БД для тестов
# "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

@pytest_asyncio.fixture(scope="session")      # scope="function" - создание
async def test_engine():                      # новой бд для каждого теста
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_sessionmaker(test_engine):
    return sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def app_test(async_sessionmaker):
    async def _get_db():
        async with async_sessionmaker() as session:
            try:
                yield session
            finally:
                await session.rollback()

    prod_app.dependency_overrides[get_async_db] = _get_db
    yield prod_app
    prod_app.dependency_overrides.clear()  # Очистка после тестов


@pytest_asyncio.fixture(scope="function")
async def client(app_test: FastAPI):
    transport = ASGITransport(app=app_test)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c



#####------------------------##########

import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from app.main import app as prod_app
from app.database import Base
from app.db_depends import get_async_db


TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"


# -------------------------
# ENGINE (ОДИН НА ВСЕ ТЕСТЫ)
# -------------------------
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)


# -------------------------
# SESSION FACTORY
# -------------------------
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


# -------------------------
# FIXTURE: DATABASE TRANSACTION (KEY PART)
# -------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.connect() as connection:
        # начинаем транзакцию
        trans = await connection.begin()

        # создаём session, привязанную к этому connection
        session = TestingSessionLocal(bind=connection)

        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()  # ВСЕГДА откатывает изменения
            await connection.close()


# -------------------------
# FASTAPI APP OVERRIDE
# -------------------------
@pytest_asyncio.fixture(scope="function")
async def app_test(db_session):
    async def _get_db():
        yield db_session  # используем уже готовую session

    prod_app.dependency_overrides[get_async_db] = _get_db

    yield prod_app

    prod_app.dependency_overrides.clear()


# -------------------------
# HTTP CLIENT
# -------------------------
@pytest_asyncio.fixture(scope="function")
async def client(app_test: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=app_test),
        base_url="http://testserver",
    ) as c:
        yield c