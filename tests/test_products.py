import pytest
from sqlalchemy import select
from app.models import Product
from decimal import Decimal

# get_all_products, get_products_by_category, get_product, create_product, update_product, delete_product
@pytest.mark.asyncio
async def test_create_and_get_product(client, seller_token, category, async_sessionmaker):
    # Нужно создать категорию и ,возможно, поменять json на data
    r = await client.post(
        "/products/",
        json={"name": "Phone", "price": "100", "stock": "5", "category_id": str(category.id)},
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "Phone"
    assert created["price"] == Decimal("100")
    assert created["stock"] == 5
    assert created["category_id"] == 1
    assert "id" in created

    async with async_sessionmaker() as session:
        product = (await session.execute(select(Product).filter(Product.id == created["id"]))).scalars().first()
        assert product is not None
        assert product.name == "Phone"
        assert product.price == Decimal("100")

    r2 = await client.get(f"/products/{created['id']}")
    assert r2.status_code == 200
    assert r2.json() == created


@pytest.mark.asyncio
async def test_get_product_not_found(client):
    r = await client.get("/products/999999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Product not found or inactive"


@pytest.mark.asyncio
async def test_update_product(client):
    r = await client.post("/products", json={"name": "Orange", "price": 3.0})
    assert r.status_code == 200
    created = r.json()

    r2 = await client.put(f"/products/{created['id']}", json={"name": "Orange Updated", "price": 3.5})
    assert r2.status_code == 200
    updated = r2.json()
    assert updated["name"] == "Orange Updated"
    assert updated["price"] == 3.5


@pytest.mark.asyncio
async def test_delete_product(client):
    r = await client.post("/products", json={"name": "Grape", "price": 4.0})
    assert r.status_code == 200
    created = r.json()

    r2 = await client.delete(f"/products/{created['id']}")
    assert r2.status_code == 204

    r3 = await client.get(f"/products/{created['id']}")
    assert r3.status_code == 404
    assert r3.json()["detail"] == "Item not found"


@pytest.mark.asyncio
async def test_get_all_products(client):
    await client.post("/products", json={"name": "Apple", "price": 1.5})
    await client.post("/products", json={"name": "Banana", "price": 2.0})

    r = await client.get("/products")
    assert r.status_code == 200
    products = r.json()
    assert len(products) > 1
    assert products[0]["name"] == "Apple"
    assert products[1]["name"] == "Banana"


############################

from fastapi.testclient import TestClient


def test_protected_endpoint_with_fixture(test_client: TestClient, test_user_token):
    token = test_user_token(username="testuser")
    response = test_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "testuser"


def test_protected_endpoint_no_token(test_client: TestClient):
    response = test_client.get("/protected")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_protected_endpoint_invalid_token(test_client: TestClient):
    response = test_client.get("/protected", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


#############-----------------------###################

import pytest
from httpx import AsyncClient

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.auth import get_current_seller
from app.models.users import User


# -------------------------
# AUTH OVERRIDE (seller)
# -------------------------
async def override_get_current_seller():
    return User(id=1, email="test@test.com", role="seller")


# -------------------------
# CATEGORY FIXTURE
# -------------------------
@pytest.fixture
async def category(async_sessionmaker):
    async with async_sessionmaker() as session:
        cat = CategoryModel(
            name="Test category",
            is_active=True,
        )
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat


# -------------------------
# CREATE PRODUCT
# -------------------------
@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, category):
    response = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Nice phone",
            "price": 100,
            "stock": 10,
            "category_id": category.id,
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "Phone"
    assert data["price"] == 100
    assert data["category_id"] == category.id


# -------------------------
# GET PRODUCT BY ID
# -------------------------
@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, category):
    create = await client.post(
        "/products/",
        data={
            "name": "Laptop",
            "description": "Gaming",
            "price": 2000,
            "stock": 5,
            "category_id": category.id,
        },
    )

    product_id = create.json()["id"]

    response = await client.get(f"/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Laptop"


# -------------------------
# GET ALL PRODUCTS
# -------------------------
@pytest.mark.asyncio
async def test_get_all_products(client: AsyncClient, category):
    await client.post(
        "/products/",
        data={
            "name": "A",
            "description": "A",
            "price": 10,
            "stock": 1,
            "category_id": category.id,
        },
    )

    response = await client.get("/products/")

    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


# -------------------------
# UPDATE PRODUCT
# -------------------------
@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, category):
    create = await client.post(
        "/products/",
        data={
            "name": "Old",
            "description": "Old desc",
            "price": 10,
            "stock": 1,
            "category_id": category.id,
        },
    )

    product_id = create.json()["id"]

    response = await client.put(
        f"/products/{product_id}",
        data={
            "name": "New",
            "description": "New desc",
            "price": 20,
            "stock": 2,
            "category_id": category.id,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New"


# -------------------------
# DELETE PRODUCT (soft delete)
# -------------------------
@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, category):
    create = await client.post(
        "/products/",
        data={
            "name": "To delete",
            "description": "X",
            "price": 10,
            "stock": 1,
            "category_id": category.id,
        },
    )

    product_id = create.json()["id"]

    response = await client.delete(f"/products/{product_id}")

    assert response.status_code == 200

    # после удаления должен быть 404 (is_active=False)
    get = await client.get(f"/products/{product_id}")
    assert get.status_code == 404


# -------------------------
# NOT FOUND CASE
# -------------------------
@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    response = await client.get("/products/999999")

    assert response.status_code == 404