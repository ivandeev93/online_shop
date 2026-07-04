import pytest
from sqlalchemy import select
from app.models.products import Product
from decimal import Decimal

# get_all_products, get_products_by_category, get_product, create_product, update_product, delete_product
@pytest.mark.asyncio
async def test_create_and_get_product(client, seller_token, category, async_sessionmaker_fixture):

    r = await client.post(
        "/products/",
        data={"name": "Phone", "description": "Test phone", "price": "100", "stock": "5", "category_id": str(category.id)},
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 201
    created = r.json()

    # Проверка ответа API
    assert created["id"] is not None
    assert created["name"] == "Phone"
    assert created["description"] == "Test phone"
    assert Decimal(created["price"]) == Decimal("100.00")
    assert created["stock"] == 5
    assert created["category_id"] == category.id
    assert created["image_url"] is None
    assert created["is_active"] is True
    assert Decimal(created["rating"]) == Decimal("0.00")

    # Проверка создания товара в бд
    async with async_sessionmaker_fixture() as session:
        product = await session.scalar(
            select(Product).where(Product.id == created["id"])
        )
        assert product is not None
        assert product.name == "Phone"
        assert product.description == "Test phone"
        assert product.price == Decimal("100.00")
        assert product.stock == 5
        assert product.category_id == category.id
        assert product.image_url is None
        assert product.is_active is True

    r2 = await client.get(f"/products/{created['id']}")
    assert r2.status_code == 200
    assert r2.json() == created


@pytest.mark.asyncio
async def test_create_product_invalid_category(client, seller_token):

    r = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Test phone",
            "price": "100",
            "stock": "5",
            "category_id": "999",
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 400
    assert r.json()["detail"] == "Category not found or inactive"


@pytest.mark.asyncio
async def test_create_product_buyer_forbidden(client, buyer_token, category):

    r = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Test phone",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_product_not_found(client):

    r = await client.get("/products/999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Product not found or inactive"


@pytest.mark.asyncio
async def test_get_products_by_category(
    client,
    seller_token,
    category,
):

    for i in range(2):
        r = await client.post(
            "/products/",
            data={
                "name": f"Phone {i}",
                "description": "Test phone",
                "price": "100",
                "stock": "5",
                "category_id": str(category.id),
            },
            headers={"Authorization": f"Bearer {seller_token}"},
        )

        assert r.status_code == 201

    r = await client.get(f"/products/category/{category.id}")

    assert r.status_code == 200

    products = r.json()

    assert len(products) == 2
    assert products[0]["category_id"] == category.id
    assert products[1]["category_id"] == category.id


@pytest.mark.asyncio
async def test_get_products_by_invalid_category(client):

    r = await client.get("/products/category/999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Category not found or inactive"


@pytest.mark.asyncio
async def test_get_all_products(
    client,
    seller_token,
    category,
):

    for i in range(3):
        await client.post(
            "/products/",
            data={
                "name": f"Phone {i}",
                "description": "Test",
                "price": "100",
                "stock": "5",
                "category_id": str(category.id),
            },
            headers={"Authorization": f"Bearer {seller_token}"},
        )

    r = await client.get("/products/")

    assert r.status_code == 200

    body = r.json()

    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_get_products_invalid_price_range(client):

    r = await client.get(
        "/products/?min_price=100&max_price=50"
    )

    assert r.status_code == 400
    assert r.json()["detail"] == "min_price не может быть больше max_price"


@pytest.mark.asyncio
async def test_update_product(
    client,
    seller_token,
    category,
):

    create = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Old description",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    product = create.json()

    r = await client.put(
        f"/products/{product['id']}",
        data={
            "name": "iPhone",
            "description": "New description",
            "price": "150",
            "stock": "10",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 200

    updated = r.json()

    assert updated["name"] == "iPhone"
    assert updated["description"] == "New description"
    assert Decimal(updated["price"]) == Decimal("150.00")
    assert updated["stock"] == 10


@pytest.mark.asyncio
async def test_update_product_not_found(
    client,
    seller_token,
    category,
):

    r = await client.put(
        "/products/999",
        data={
            "name": "Phone",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_update_foreign_product(
    client,
    seller_token,
    token_factory,
    category,
):

    second_seller = await token_factory(
        "seller2@test.com",
        "seller",
    )

    create = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    product = create.json()

    r = await client.put(
        f"/products/{product['id']}",
        data={
            "name": "Hack",
            "description": "Hack",
            "price": "1",
            "stock": "1",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {second_seller}"},
    )

    assert r.status_code == 403
    assert r.json()["detail"] == "You can only update your own products"


@pytest.mark.asyncio
async def test_update_product_invalid_category(
    client,
    seller_token,
    category,
):

    create = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    product = create.json()

    r = await client.put(
        f"/products/{product['id']}",
        data={
            "name": "Phone",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": "999",
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 400
    assert r.json()["detail"] == "Category not found or inactive"


@pytest.mark.asyncio
async def test_delete_product(
    client,
    seller_token,
    category,
):

    create = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    product = create.json()

    r = await client.delete(
        f"/products/{product['id']}",
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = await client.get(f"/products/{product['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_foreign_product(
    client,
    seller_token,
    token_factory,
    category,
):

    second_seller = await token_factory(
        "seller2@test.com",
        "seller",
    )

    create = await client.post(
        "/products/",
        data={
            "name": "Phone",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    product = create.json()

    r = await client.delete(
        f"/products/{product['id']}",
        headers={"Authorization": f"Bearer {second_seller}"},
    )

    assert r.status_code == 403
    assert r.json()["detail"] == "You can only delete your own products"


@pytest.mark.asyncio
async def test_delete_product_not_found(
    client,
    seller_token,
):

    r = await client.delete(
        "/products/999",
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Product not found or inactive"
##############################

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