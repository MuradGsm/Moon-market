import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.products.models import Product

PAYLOAD = {"title": "Phone", "description": "Nice phone", "price": "199.99", "stock": 5}


async def create_product(client: AsyncClient, headers: dict, **overrides) -> dict:
    response = await client.post("/products", json={**PAYLOAD, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- search ----------


async def test_search_is_case_insensitive(client: AsyncClient, seller: dict):
    await create_product(client, seller["headers"], title="iPhone 15")
    await create_product(client, seller["headers"], title="Galaxy S24")

    response = await client.get("/products", params={"search": "IPHONE"})

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "iPhone 15"


async def test_search_escapes_like_wildcards(client: AsyncClient, seller: dict):
    for title in ("100% cotton", "100 cotton", "a_b", "axb"):
        await create_product(client, seller["headers"], title=title)

    percent = (await client.get("/products", params={"search": "%"})).json()
    underscore = (await client.get("/products", params={"search": "_"})).json()

    assert [i["title"] for i in percent["items"]] == ["100% cotton"]
    assert [i["title"] for i in underscore["items"]] == ["a_b"]


async def test_search_combined_with_price_filter(client: AsyncClient, seller: dict):
    await create_product(client, seller["headers"], title="Phone cheap", price="10.00")
    await create_product(client, seller["headers"], title="Phone pricey", price="900.00")

    response = await client.get("/products", params={"search": "phone", "min_price": 100})

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Phone pricey"


async def test_search_rejects_blank_value(client: AsyncClient):
    response = await client.get("/products", params={"search": "   "})

    assert response.status_code == 422


# ---------- cache ----------


async def test_list_is_cached_with_ttl(client: AsyncClient, seller: dict, redis):
    await create_product(client, seller["headers"])

    await client.get("/products")

    keys = [key async for key in redis.scan_iter("products:list:*")]
    assert len(keys) == 1
    assert 0 < await redis.ttl(keys[0]) <= 60


async def test_second_request_is_served_from_cache(
    client: AsyncClient, seller: dict, session_factory
):
    product = await create_product(client, seller["headers"], title="Original")
    first = await client.get("/products")

    # Меняем строку в обход API: кэш не инвалидируется
    async with session_factory() as session:
        row = await session.get(Product, uuid.UUID(product["id"]))
        row.title = "Changed in DB"
        await session.commit()

    second = await client.get("/products")

    assert first.json() == second.json()
    assert second.json()["items"][0]["title"] == "Original"


async def test_different_filters_use_different_cache_keys(
    client: AsyncClient, seller: dict, redis
):
    await create_product(client, seller["headers"])

    await client.get("/products")
    await client.get("/products", params={"limit": 1})

    keys = [key async for key in redis.scan_iter("products:list:*")]
    assert len(keys) == 2


async def test_writes_invalidate_cache(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"], title="First")
    await client.get("/products")  # прогрели кэш

    await create_product(client, seller["headers"], title="Second")
    assert (await client.get("/products")).json()["total"] == 2

    await client.patch(
        f"/products/{product['id']}", json={"title": "Renamed"}, headers=seller["headers"]
    )
    titles = {i["title"] for i in (await client.get("/products")).json()["items"]}
    assert "Renamed" in titles

    await client.delete(f"/products/{product['id']}", headers=seller["headers"])
    assert (await client.get("/products")).json()["total"] == 1


# ---------- redis is down ----------


@pytest.fixture
def broken_redis(redis, monkeypatch):
    for method in ("get", "set", "setex", "incr"):
        monkeypatch.setattr(
            redis, method, AsyncMock(side_effect=RedisConnectionError("redis is down"))
        )
    return redis


async def test_api_works_when_redis_is_down(
    client: AsyncClient, seller: dict, broken_redis
):
    await create_product(client, seller["headers"]) 

    response = await client.get("/products")

    assert response.status_code == 200
    assert response.json()["total"] == 1