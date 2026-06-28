import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sqlalchemy import delete
from app.main import app as prod_app
from app.database import Base
from app.db_depends import get_async_db

from app.auth import create_access_token
from app.models.users import User as UserModel

import pytest



TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # отдельная БД для тестов
# "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

@pytest_asyncio.fixture(scope="session")      # scope="function" - создание
async def test_engine():                      # новой бд для каждого теста
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_sessionmaker(test_engine):
    return sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db(async_sessionmaker):
    async with async_sessionmaker() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(delete(table))
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def app_test(async_sessionmaker):
    async def _get_db():
        async with async_sessionmaker() as session:
            try:
                yield session
            finally:
                await session.close()

    prod_app.dependency_overrides[get_async_db] = _get_db

    yield prod_app

    prod_app.dependency_overrides.clear()  # Очистка после тестов


@pytest_asyncio.fixture(scope="function")
async def client(app_test: FastAPI):
    transport = ASGITransport(app=app_test)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# Фикстура для продавца
@pytest_asyncio.fixture
async def seller_token(async_sessionmaker):
    async with async_sessionmaker() as session:
        user = UserModel(
            email="seller@test.com",
            hashed_password="fake",
            role="seller",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        email = user.email
        role = user.role

    return create_access_token({
        "sub": email,
        "role": role,
    })


# Фикстура для покупателя
@pytest_asyncio.fixture
async def buyer_token(async_sessionmaker):
    async with async_sessionmaker() as session:
        user = UserModel(
            email="buyer@test.com",
            hashed_password="fake",
            role="buyer",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        email = user.email
        role = user.role

    return create_access_token({
        "sub": email,
        "role": role,
    })