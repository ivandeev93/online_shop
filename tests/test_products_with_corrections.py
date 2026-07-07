import pytest
from decimal import Decimal
from sqlalchemy import select

from app.models.products import Product


@pytest.mark.asyncio
async def test_create_and_get_product(
    client,
    category,
    product_factory,
    async_sessionmaker_fixture,
):
    product = await product_factory(category.id)

    assert product["id"] is not None
    assert product["name"] == "Phone"
    assert product["description"] == "Test phone"
    assert Decimal(product["price"]) == Decimal("100.00")
    assert product["stock"] == 5
    assert product["category_id"] == category.id
    assert product["image_url"] is None
    assert product["is_active"] is True

    async with async_sessionmaker_fixture() as session:
        db_product = await session.scalar(
            select(Product).where(Product.id == product["id"])
        )

        assert db_product is not None
        assert db_product.name == "Phone"

    response = await client.get(f"/products/{product['id']}")

    assert response.status_code == 200
    assert response.json() == product


@pytest.mark.asyncio
async def test_update_product(
    client,
    seller_token,
    category,
    product_factory,
):
    product = await product_factory(
        category.id,
        description="Old description",
    )

    response = await client.put(
        f"/products/{product['id']}",
        data={
            "name": "iPhone",
            "description": "New description",
            "price": "150",
            "stock": "10",
            "category_id": str(category.id),
        },
        headers={
            "Authorization": f"Bearer {seller_token}"
        },
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["name"] == "iPhone"
    assert updated["description"] == "New description"
    assert Decimal(updated["price"]) == Decimal("150.00")
    assert updated["stock"] == 10


@pytest.mark.asyncio
async def test_update_foreign_product(
    client,
    token_factory,
    category,
    product_factory,
):
    second_seller = await token_factory(
        "seller2@test.com",
        "seller",
    )

    product = await product_factory(category.id)

    response = await client.put(
        f"/products/{product['id']}",
        data={
            "name": "Hack",
            "description": "Hack",
            "price": "1",
            "stock": "1",
            "category_id": str(category.id),
        },
        headers={
            "Authorization": f"Bearer {second_seller}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You can only update your own products"


@pytest.mark.asyncio
async def test_delete_product(
    client,
    seller_token,
    category,
    product_factory,
):
    product = await product_factory(category.id)

    response = await client.delete(
        f"/products/{product['id']}",
        headers={
            "Authorization": f"Bearer {seller_token}"
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = await client.get(f"/products/{product['id']}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_foreign_product(
    client,
    token_factory,
    category,
    product_factory,
):
    second_seller = await token_factory(
        "seller2@test.com",
        "seller",
    )

    product = await product_factory(category.id)

    response = await client.delete(
        f"/products/{product['id']}",
        headers={
            "Authorization": f"Bearer {second_seller}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You can only delete your own products"


@pytest.mark.asyncio
async def test_get_all_products(
    client,
    category,
    product_factory,
):
    for i in range(3):
        await product_factory(
            category.id,
            name=f"Phone {i}",
        )

    response = await client.get("/products/")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_get_all_products_pagination(
    client,
    category,
    product_factory,
):
    for i in range(25):
        await product_factory(
            category.id,
            name=f"Phone {i}",
        )

    response = await client.get(
        "/products?page=2&page_size=20"
    )

    body = response.json()

    assert response.status_code == 200
    assert body["total"] == 25
    assert body["page"] == 2
    assert body["page_size"] == 20
    assert len(body["items"]) == 5

    assert body["items"][0]["name"] == "Phone 20"
    assert body["items"][-1]["name"] == "Phone 24"


@pytest.mark.asyncio
async def test_get_products_by_price_range(
    client,
    category,
    product_factory,
):
    for price in (50, 100, 150):
        await product_factory(
            category.id,
            name=f"Phone {price}",
            price=str(price),
        )

    response = await client.get(
        "/products?min_price=80&max_price=120"
    )

    body = response.json()

    assert response.status_code == 200
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Phone 100"


@pytest.mark.asyncio
async def test_get_products_in_stock_filter(
    client,
    category,
    product_factory,
):
    await product_factory(
        category.id,
        name="Available",
        stock="5",
    )

    await product_factory(
        category.id,
        name="Unavailable",
        stock="0",
    )

    response = await client.get(
        "/products?in_stock=true"
    )

    body = response.json()

    assert response.status_code == 200
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Available"