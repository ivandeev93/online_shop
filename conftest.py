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

    prod_app.dependency_overrides[get_db] = _get_db
    async with async_sessionmaker() as session:
        await session.execute(delete(Item))
        await session.commit()
    yield prod_app
    prod_app.dependency_overrides.clear()  # Очистка после тестов


@pytest_asyncio.fixture(scope="function")
async def client(app_test: FastAPI):
    transport = ASGITransport(app=app_test)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c