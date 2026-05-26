import pytest
from sqlalchemy import select
from app.models import Product

# get_all_products, get_products_by_category, get_product, create_product, update_product, delete_product
@pytest.mark.asyncio
async def test_create_and_get_product(client, async_sessionmaker):
    r = await client.post("/products", json={"name": "Apple", "price": 1.5})
    assert r.status_code == 200
    created = r.json()
    assert created["name"] == "Apple"
    assert created["price"] == 1.5
    assert "id" in created

    async with async_sessionmaker() as session:
        product = (await session.execute(select(Product).filter(Product.id == created["id"]))).scalars().first()
        assert product is not None
        assert product.name == "Apple"
        assert product.price == 1.5

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