import asyncio
import uuid
from decimal import Decimal

from httpx import AsyncClient, Response

PRODUCT = {"title": "Phone", "description": "Nice phone", "price": "100.00", "stock": 5}


async def create_product(client: AsyncClient, headers: dict, **overrides) -> dict:
    response = await client.post("/products", json={**PRODUCT, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def line(product: dict, quantity: int = 1) -> dict:
    return {"product_id": product["id"], "quantity": quantity}


async def place_order(client: AsyncClient, headers: dict, *items: dict) -> Response:
    return await client.post("/orders", json={"items": list(items)}, headers=headers)


async def get_stock(client: AsyncClient, product: dict) -> int:
    return (await client.get(f"/products/{product['id']}")).json()["stock"]


# ---------- create ----------


async def test_create_order_success(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"])

    response = await place_order(client, buyer["headers"], line(product, 2))

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "pending"
    assert data["buyer_id"] == buyer["id"]
    assert Decimal(data["total_amount"]) == Decimal("200.00")
    assert len(data["items"]) == 1
    assert data["items"][0]["product_title"] == "Phone"
    assert Decimal(data["items"][0]["unit_price"]) == Decimal("100.00")
    assert data["items"][0]["quantity"] == 2
    assert await get_stock(client, product) == 3


async def test_create_order_with_multiple_items(client: AsyncClient, seller: dict, buyer: dict):
    first = await create_product(client, seller["headers"], title="A", price="10.50")
    second = await create_product(client, seller["headers"], title="B", price="20.00")

    response = await place_order(client, buyer["headers"], line(first, 2), line(second, 1))

    assert response.status_code == 201, response.text
    assert Decimal(response.json()["total_amount"]) == Decimal("41.00")


async def test_create_order_requires_auth(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])

    response = await place_order(client, {}, line(product))

    assert response.status_code == 401


async def test_insufficient_stock_keeps_stock_untouched(
    client: AsyncClient, seller: dict, buyer: dict
):
    product = await create_product(client, seller["headers"], stock=2)

    response = await place_order(client, buyer["headers"], line(product, 3))

    assert response.status_code == 409
    assert await get_stock(client, product) == 2


async def test_order_is_all_or_nothing(client: AsyncClient, seller: dict, buyer: dict):
    enough = await create_product(client, seller["headers"], title="Enough", stock=10)
    scarce = await create_product(client, seller["headers"], title="Scarce", stock=1)

    response = await place_order(client, buyer["headers"], line(enough, 2), line(scarce, 5))

    assert response.status_code == 409
    assert await get_stock(client, enough) == 10  # первая позиция тоже откатилась
    assert await get_stock(client, scarce) == 1


async def test_unknown_product_is_rejected(client: AsyncClient, buyer: dict):
    response = await client.post(
        "/orders",
        json={"items": [{"product_id": str(uuid.uuid4()), "quantity": 1}]},
        headers=buyer["headers"],
    )

    assert response.status_code == 409


async def test_inactive_product_is_rejected(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"])
    await client.delete(f"/products/{product['id']}", headers=seller["headers"])

    response = await place_order(client, buyer["headers"], line(product))

    assert response.status_code == 409


async def test_seller_cannot_order_own_product(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])

    response = await place_order(client, seller["headers"], line(product))

    assert response.status_code == 403
    assert await get_stock(client, product) == 5


async def test_invalid_payload_is_rejected(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"])

    empty = await client.post("/orders", json={"items": []}, headers=buyer["headers"])
    zero_qty = await place_order(client, buyer["headers"], line(product, 0))
    duplicates = await place_order(client, buyer["headers"], line(product), line(product))

    assert empty.status_code == 422
    assert zero_qty.status_code == 422
    assert duplicates.status_code == 422


async def test_price_is_snapshotted(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"])
    order = (await place_order(client, buyer["headers"], line(product))).json()

    await client.patch(
        f"/products/{product['id']}",
        json={"price": "999.00", "title": "Renamed"},
        headers=seller["headers"],
    )

    fetched = (await client.get(f"/orders/{order['id']}", headers=buyer["headers"])).json()
    assert Decimal(fetched["items"][0]["unit_price"]) == Decimal("100.00")
    assert fetched["items"][0]["product_title"] == "Phone"
    assert Decimal(fetched["total_amount"]) == Decimal("100.00")


async def test_concurrent_orders_do_not_oversell(
    client: AsyncClient, seller: dict, buyer: dict
):
    """Главный тест этапа: 10 параллельных заказов на 5 штук товара."""
    product = await create_product(client, seller["headers"], stock=5)

    responses = await asyncio.gather(
        *(place_order(client, buyer["headers"], line(product)) for _ in range(10))
    )

    codes = sorted(r.status_code for r in responses)
    assert codes.count(201) == 5, codes
    assert codes.count(409) == 5, codes
    assert await get_stock(client, product) == 0


async def test_order_invalidates_products_cache(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"], stock=5)
    warm = await client.get("/products")  # прогрели кэш
    assert warm.json()["items"][0]["stock"] == 5

    await place_order(client, buyer["headers"], line(product, 2))

    fresh = await client.get("/products")
    assert fresh.json()["items"][0]["stock"] == 3


# ---------- read ----------


async def test_list_returns_only_own_orders(
    client: AsyncClient, seller: dict, buyer: dict, make_user
):
    other_buyer = await make_user("other-buyer@example.com")
    product = await create_product(client, seller["headers"], stock=10)
    await place_order(client, buyer["headers"], line(product))
    await place_order(client, buyer["headers"], line(product))
    await place_order(client, other_buyer["headers"], line(product))

    mine = (await client.get("/orders", headers=buyer["headers"])).json()
    paid = (
        await client.get("/orders", params={"status": "paid"}, headers=buyer["headers"])
    ).json()

    assert mine["total"] == 2
    assert all(o["buyer_id"] == buyer["id"] for o in mine["items"])
    assert paid["total"] == 0


async def test_get_order_access_rules(
    client: AsyncClient, seller: dict, buyer: dict, admin: dict, make_user
):
    other_buyer = await make_user("other-buyer@example.com")
    product = await create_product(client, seller["headers"])
    order = (await place_order(client, buyer["headers"], line(product))).json()
    url = f"/orders/{order['id']}"

    assert (await client.get(url, headers=buyer["headers"])).status_code == 200
    assert (await client.get(url, headers=admin["headers"])).status_code == 200
    assert (await client.get(url, headers=other_buyer["headers"])).status_code == 404
    assert (await client.get(url)).status_code == 401


# ---------- cancel ----------


async def test_cancel_restores_stock(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"], stock=5)
    order = (await place_order(client, buyer["headers"], line(product, 3))).json()
    assert await get_stock(client, product) == 2

    response = await client.post(f"/orders/{order['id']}/cancel", headers=buyer["headers"])

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert await get_stock(client, product) == 5


async def test_cannot_cancel_twice(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"], stock=5)
    order = (await place_order(client, buyer["headers"], line(product, 3))).json()
    await client.post(f"/orders/{order['id']}/cancel", headers=buyer["headers"])

    response = await client.post(f"/orders/{order['id']}/cancel", headers=buyer["headers"])

    assert response.status_code == 409
    assert await get_stock(client, product) == 5  # остаток не вернулся дважды


async def test_other_buyer_cannot_cancel(
    client: AsyncClient, seller: dict, buyer: dict, make_user
):
    other_buyer = await make_user("other-buyer@example.com")
    product = await create_product(client, seller["headers"], stock=5)
    order = (await place_order(client, buyer["headers"], line(product, 2))).json()

    response = await client.post(
        f"/orders/{order['id']}/cancel", headers=other_buyer["headers"]
    )

    assert response.status_code == 404
    assert await get_stock(client, product) == 3


async def test_admin_can_cancel_any_order(
    client: AsyncClient, seller: dict, buyer: dict, admin: dict
):
    product = await create_product(client, seller["headers"], stock=5)
    order = (await place_order(client, buyer["headers"], line(product, 2))).json()

    response = await client.post(f"/orders/{order['id']}/cancel", headers=admin["headers"])

    assert response.status_code == 200
    assert await get_stock(client, product) == 5