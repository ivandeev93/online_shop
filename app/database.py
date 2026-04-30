from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
import os


# --------------- Асинхронное подключение к PostgreSQL -------------------------

# Строка подключения для PostgreSQl
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# Создаём Engine
async_engine = create_async_engine(DATABASE_URL, echo=True)

# Настраиваем фабрику сеансов
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
                                         #expire_on_commit - предотвращает устаревание объектов после db.commit()
                                         #делая db.refresh() избыточным.
class Base(DeclarativeBase):
    pass
