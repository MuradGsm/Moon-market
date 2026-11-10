import uuid
from decimal import Decimal

from httpx import AsyncClient

PAYLOAD = {"title": "Phone", "description": "Nice phone", "price": "199.99", "stock": 5}


async def create_product(client: AsyncClient, headers: dict, **overrides) -> dict:
    response = await client.post("/products", json={**PAYLOAD, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- create ----------


async def test_seller_creates_product(client: AsyncClient, seller: dict):
    data = await create_product(client, seller["headers"])

    assert data["seller_id"] == seller["id"]
    assert data["title"] == "Phone"
    assert Decimal(data["price"]) == Decimal("199.99")
    assert data["stock"] == 5
    assert data["is_active"] is True


async def test_buyer_cannot_create_product(client: AsyncClient, buyer: dict):
    response = await client.post("/products", json=PAYLOAD, headers=buyer["headers"])

    assert response.status_code == 403


async def test_create_requires_auth(client: AsyncClient):
    response = await client.post("/products", json=PAYLOAD)

    assert response.status_code == 401


async def test_create_rejects_negative_price(client: AsyncClient, seller: dict):
    response = await client.post(
        "/products", json={**PAYLOAD, "price": "-1"}, headers=seller["headers"]
    )

    assert response.status_code == 422


async def test_create_rejects_too_many_decimals(client: AsyncClient, seller: dict):
    response = await client.post(
        "/products", json={**PAYLOAD, "price": "10.999"}, headers=seller["headers"]
    )

    assert response.status_code == 422


async def test_create_ignores_seller_id_from_body(
    client: AsyncClient, seller: dict, other_seller: dict
):
    data = await create_product(client, seller["headers"], seller_id=other_seller["id"])

    assert data["seller_id"] == seller["id"]


# ---------- get ----------


async def test_get_product_is_public(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])

    response = await client.get(f"/products/{product['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == product["id"]


async def test_get_unknown_product(client: AsyncClient):
    response = await client.get(f"/products/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_get_invalid_uuid(client: AsyncClient):
    response = await client.get("/products/not-a-uuid")

    assert response.status_code == 422


# ---------- list ----------


async def test_list_pagination(client: AsyncClient, seller: dict):
    for i in range(5):
        await create_product(client, seller["headers"], title=f"Item {i}")

    response = await client.get("/products", params={"limit": 2, "offset": 2})

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 2


async def test_list_filter_by_price(client: AsyncClient, seller: dict):
    for price in ("10.00", "50.00", "100.00"):
        await create_product(client, seller["headers"], price=price)

    response = await client.get("/products", params={"min_price": 20, "max_price": 60})

    data = response.json()
    assert data["total"] == 1
    assert Decimal(data["items"][0]["price"]) == Decimal("50.00")


async def test_list_sort_by_price_asc(client: AsyncClient, seller: dict):
    for price in ("50.00", "10.00", "100.00"):
        await create_product(client, seller["headers"], price=price)

    response = await client.get("/products", params={"sort": "price", "order": "asc"})

    prices = [Decimal(p["price"]) for p in response.json()["items"]]
    assert prices == [Decimal("10.00"), Decimal("50.00"), Decimal("100.00")]


async def test_list_filter_by_seller(client: AsyncClient, seller: dict, other_seller: dict):
    await create_product(client, seller["headers"])
    await create_product(client, other_seller["headers"])

    response = await client.get("/products", params={"seller_id": seller["id"]})

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["seller_id"] == seller["id"]


async def test_list_rejects_invalid_params(client: AsyncClient):
    assert (await client.get("/products", params={"limit": 1000})).status_code == 422
    assert (
        await client.get("/products", params={"min_price": 100, "max_price": 10})
    ).status_code == 422
    assert (await client.get("/products", params={"sort": "title"})).status_code == 422
    assert (await client.get("/products", params={"unknown": 1})).status_code == 422


# ---------- update ----------


async def test_owner_updates_product_partially(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}", json={"title": "New title"}, headers=seller["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert Decimal(data["price"]) == Decimal("199.99")  # остальное не тронуто


async def test_other_seller_cannot_update(
    client: AsyncClient, seller: dict, other_seller: dict
):
    product = await create_product(client, seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}", json={"title": "Hack"}, headers=other_seller["headers"]
    )

    assert response.status_code == 403


async def test_admin_can_update_any_product(client: AsyncClient, seller: dict, admin: dict):
    product = await create_product(client, seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}", json={"stock": 99}, headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["stock"] == 99


async def test_buyer_cannot_update(client: AsyncClient, seller: dict, buyer: dict):
    product = await create_product(client, seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}", json={"title": "Hack"}, headers=buyer["headers"]
    )

    assert response.status_code == 403


async def test_update_rejects_null_title(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}", json={"title": None}, headers=seller["headers"]
    )

    assert response.status_code == 422


async def test_update_rejects_unknown_field(client: AsyncClient, seller: dict, other_seller: dict):
    product = await create_product(client, seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}",
        json={"seller_id": other_seller["id"]},
        headers=seller["headers"],
    )

    assert response.status_code == 422


async def test_update_unknown_product(client: AsyncClient, seller: dict):
    response = await client.patch(
        f"/products/{uuid.uuid4()}", json={"title": "x"}, headers=seller["headers"]
    )

    assert response.status_code == 404


# ---------- delete (soft) ----------


async def test_owner_soft_deletes_product(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])

    response = await client.delete(f"/products/{product['id']}", headers=seller["headers"])

    assert response.status_code == 204
    assert (await client.get(f"/products/{product['id']}")).status_code == 404
    assert (await client.get("/products")).json()["total"] == 0


async def test_other_seller_cannot_delete(
    client: AsyncClient, seller: dict, other_seller: dict
):
    product = await create_product(client, seller["headers"])

    response = await client.delete(
        f"/products/{product['id']}", headers=other_seller["headers"]
    )

    assert response.status_code == 403


async def test_owner_can_restore_deleted_product(client: AsyncClient, seller: dict):
    product = await create_product(client, seller["headers"])
    await client.delete(f"/products/{product['id']}", headers=seller["headers"])

    response = await client.patch(
        f"/products/{product['id']}", json={"is_active": True}, headers=seller["headers"]
    )

    assert response.status_code == 200
    assert (await client.get(f"/products/{product['id']}")).status_code == 200