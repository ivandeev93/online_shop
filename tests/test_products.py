import pytest
from sqlalchemy import select
from app.models.products import Product
from decimal import Decimal


@pytest.mark.asyncio
async def test_create_and_get_product(client, product_factory,
                                      category, async_sessionmaker_fixture):

    created = await product_factory(category_id=category.id,)

    assert created.status_code == 201

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

    response = await client.get(f"/products/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.asyncio
async def test_create_product_invalid_category(client, seller_token):

    response = await client.post(
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

    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found or inactive"


@pytest.mark.asyncio
async def test_create_product_buyer_forbidden(client, buyer_token, category):

    response = await client.post(
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

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_product_not_found(client):

    response = await client.get("/products/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found or inactive"


@pytest.mark.asyncio
async def test_get_products_by_category(client, category, product_factory):

    for i in range(2):
        await product_factory(category_id=category.id,
                                  name=f"Phone {i}")

    response = await client.get(f"/products/category/{category.id}")

    assert response.status_code == 200

    products = response.json()

    assert len(products) == 2
    assert products[0]["category_id"] == category.id
    assert products[1]["category_id"] == category.id


@pytest.mark.asyncio
async def test_get_products_by_invalid_category(client):

    response = await client.get("/products/category/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found or inactive"


@pytest.mark.asyncio
async def test_get_all_products(client, category, product_factory):

    for i in range(3):
        await product_factory(
            category_id=category.id,
            name=f"Phone {i}",
            description="Test",
        )

    response = await client.get("/products/")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_get_products_invalid_price_range(client):

    response = await client.get(
        "/products/?min_price=100&max_price=50"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "min_price не может быть больше max_price"


@pytest.mark.asyncio
async def test_update_product(client, seller_token,
                              category, product_factory):

    product = await product_factory(
        category_id=category.id,
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
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["name"] == "iPhone"
    assert updated["description"] == "New description"
    assert Decimal(updated["price"]) == Decimal("150.00")
    assert updated["stock"] == 10


@pytest.mark.asyncio
async def test_update_product_not_found(client, seller_token, category):

    response = await client.put(
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

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_update_foreign_product(client, seller_token, token_factory,
                                      category, product_factory):

    second_seller = await token_factory(
        "seller2@test.com",
        "seller",
    )

    product = await product_factory(
        category_id=category.id,
        token=seller_token,
    )

    response = await client.put(
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

    assert response.status_code == 403
    assert response.json()["detail"] == "You can only update your own products"


@pytest.mark.asyncio
async def test_update_product_invalid_category(client, seller_token,
                                               product_factory, category):
    product = await product_factory(
        category_id=category.id,
    )

    response = await client.put(
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

    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found or inactive"


@pytest.mark.asyncio
async def test_delete_product(client, seller_token, product_factory, category):

    product = await product_factory(
        category_id=category.id,
    )

    response = await client.delete(
        f"/products/{product['id']}",
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = await client.get(f"/products/{product['id']}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_foreign_product(client, seller_token, token_factory,
                                      category, product_factory):

    second_seller = await token_factory(
        "seller2@test.com",
        "seller",
    )

    product = await product_factory(
        category_id=category.id,
        token=seller_token,
    )

    response = await client.delete(
        f"/products/{product['id']}",
        headers={"Authorization": f"Bearer {second_seller}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You can only delete your own products"


@pytest.mark.asyncio
async def test_delete_product_not_found(client, seller_token):

    response = await client.delete(
        "/products/999",
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found or inactive"


# Проверка пагинации
@pytest.mark.asyncio
async def test_get_all_products_pagination(client, seller_token,
                                           category, product_factory):
    # создаём 25 товаров
    for i in range(25):
        await product_factory(
            category_id=category.id,
            name=f"Phone {i}",
            description="Test",
        )

    response = await client.get("/products?page=2&page_size=20")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 25
    assert body["page"] == 2
    assert body["page_size"] == 20
    assert len(body["items"]) == 5

    # проверяем, что это действительно последние товары
    assert body["items"][0]["name"] == "Phone 20"
    assert body["items"][-1]["name"] == "Phone 24"


# Тест на выборку по цене
@pytest.mark.asyncio
async def test_get_products_by_price_range(client, category, product_factory):
    prices = [50, 100, 150]

    for price in prices:
        await product_factory(
            category_id=category.id,
            name=f"Phone {price}",
            price=str(price),
        )

    response = await client.get("/products?min_price=80&max_price=120")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Phone 100"


# Проверка фильтра в наличии
@pytest.mark.asyncio
async def test_get_products_in_stock_filter(client, product_factory, category):

    await product_factory(
        category_id=category.id,
        name="Available",
        stock="5",
    )

    await product_factory(
        category_id=category.id,
        name="Unavailable",
        stock="0",
    )

    response = await client.get("/products?in_stock=true")


    body = response.json()

    assert response.status_code == 200
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Available"