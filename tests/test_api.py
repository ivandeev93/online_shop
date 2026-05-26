from importlib import reload
import app.main as main  # импортируем модуль (понадобится для reload)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.main import Item
import pytest


# --------- Базовые проверки ---------

# Проверка GET /items/{item_id}
def test_get_item_success(client: TestClient, setup_test_data):
    r = client.get("/items/1")
    assert r.status_code == 200
    assert r.json() == {"id": 1, "name": "Laptop", "price": 999.99}


def test_get_item_not_found(client: TestClient):
    r = client.get("/items/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Item not found"}


# Проверка POST /items
def test_create_item_success(client: TestClient, db_session: Session):
    r = client.post("/items", json={"name": "Tablet", "price": 299.99})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Tablet"
    assert data["price"] == 299.99
    assert "id" in data

    # Убеждаемся, что запись реально попала в тестовую БД.
    row = db_session.query(Item).filter(Item.name == "Tablet").first()
    assert row is not None
    assert row.price == 299.99


def test_create_item_invalid_data(client: TestClient, db_session: Session):
    # Пустое имя и отрицательная цена — 422, потому что валидация в pydantic-схеме.
    r = client.post("/items", json={"name": "", "price": -10.0})
    assert r.status_code == 422
    assert "detail" in r.json()


# --------- Проверка переменной окружения ---------
def test_database_url_environment(monkeypatch, tmp_path):
    """
    Проверяем, что приложение читает DATABASE_URL при импорте модуля.
    Меняем env, перезагружаем app.main, пишем запись и проверяем её в файле БД.
    """
    db_path = tmp_path / "env.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # Перезагружаем модуль после изменения окружения.
    reload(main)

    client = TestClient(main.app)
    r = client.post("/items", json={"name": "Headphones", "price": 49.99})
    assert r.status_code == 200

    # Подключаемся напрямую к файлу и проверяем, что данные там есть.
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with Session(engine) as s:
        row = s.query(main.Item).filter(main.Item.name == "Headphones").first()
        assert row is not None
        assert row.price == 49.99

    # Возвращаем модуль в исходное состояние:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reload(main)
