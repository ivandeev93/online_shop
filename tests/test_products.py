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


# Проверка пагинации
@pytest.mark.asyncio
async def test_get_all_products_pagination(
    client,
    seller_token,
    category,
):
    # создаём 25 товаров
    for i in range(25):
        r = await client.post(
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
        assert r.status_code == 201

    r = await client.get("/products?page=2&page_size=20")

    assert r.status_code == 200

    body = r.json()

    assert body["total"] == 25
    assert body["page"] == 2
    assert body["page_size"] == 20
    assert len(body["items"]) == 5

    # проверяем, что это действительно последние товары
    assert body["items"][0]["name"] == "Phone 20"
    assert body["items"][-1]["name"] == "Phone 24"


# Тест на выборку по цене
@pytest.mark.asyncio
async def test_get_products_by_price_range(
    client,
    seller_token,
    category,
):
    prices = [50, 100, 150]

    for price in prices:
        await client.post(
            "/products/",
            data={
                "name": f"Phone {price}",
                "description": "Test",
                "price": str(price),
                "stock": "5",
                "category_id": str(category.id),
            },
            headers={"Authorization": f"Bearer {seller_token}"},
        )

    r = await client.get("/products?min_price=80&max_price=120")

    assert r.status_code == 200

    body = r.json()

    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Phone 100"


# Проверка фильтра в наличии
@pytest.mark.asyncio
async def test_get_products_in_stock_filter(
    client,
    seller_token,
    category,
):
    await client.post(
        "/products/",
        data={
            "name": "Available",
            "description": "Test",
            "price": "100",
            "stock": "5",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    await client.post(
        "/products/",
        data={
            "name": "Unavailable",
            "description": "Test",
            "price": "100",
            "stock": "0",
            "category_id": str(category.id),
        },
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    r = await client.get("/products?in_stock=true")

    assert r.status_code == 200

    body = r.json()

    assert body["total"] == 1
    assert body["items"][0]["name"] == "Available"