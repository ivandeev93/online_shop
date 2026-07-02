import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sqlalchemy import text
from app.main import app as prod_app
from app.database import Base
from app.db_depends import get_async_db

from app.auth import create_access_token
from app.models.users import User as UserModel
from app.models.categories import Category as CategoryModel

import pytest



TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"  # отдельная БД для тестов
# "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")      # scope="function" - создание
async def test_engine():                      # новой бд для каждого теста
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False},
                                 poolclass=StaticPool, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_sessionmaker_fixture(test_engine):
    return sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db(async_sessionmaker):
    async with async_sessionmaker() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE "
                "products, categories, users "
                "RESTART IDENTITY CASCADE;"
            )
        )
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def app_test(async_sessionmaker):
    async def _get_db():
        async with async_sessionmaker() as session:
            yield session


    prod_app.dependency_overrides[get_async_db] = _get_db

    yield prod_app

    prod_app.dependency_overrides.clear()  # Очистка после тестов


@pytest_asyncio.fixture(scope="function")
async def client(app_test: FastAPI):
    transport = ASGITransport(app=app_test)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture
async def token_factory(async_sessionmaker):
    async def _create_token(
        email: str,
        role: str,
        password: str = "fake",
    ) -> str:
        async with async_sessionmaker() as session:
            user = UserModel(
                email=email,
                hashed_password=password,
                role=role,
                is_active=True,
            )
            session.add(user)
            await session.commit()

        return create_access_token({
            "sub": email,
            "role": role,
        })

    return _create_token


# Фикстура для продавца
@pytest_asyncio.fixture
async def seller_token(token_factory):
    return await token_factory("seller@test.com", "seller")


# Фикстура для покупателя
@pytest_asyncio.fixture
async def buyer_token(token_factory):
    return await token_factory("buyer@test.com", "buyer")


# Фикстура для админа
@pytest_asyncio.fixture
async def admin_token(token_factory):
    return await token_factory("admin@test.com", "admin")


# Фикстура тестовой категории
@pytest_asyncio.fixture
async def category(async_sessionmaker_fixture):
    async with async_sessionmaker_fixture() as session:

        category = CategoryModel(
            name="Electronics",
            is_active=True,
        )

        session.add(category)
        await session.commit()
        await session.refresh(category)

        return category