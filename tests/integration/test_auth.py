from httpx import AsyncClient


async def test_register_success(client: AsyncClient, user_payload: dict):
    response = await client.post("/auth/register", json=user_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_payload["email"]
    assert data["role"] == "buyer"
    assert "password" not in data
    assert "hashed_password" not in data


async def test_register_lowercases_email(client: AsyncClient):
    response = await client.post(
        "/auth/register", json={"email": "Test@Example.COM", "password": "StrongPass123"}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"


async def test_register_duplicate_email(client: AsyncClient, registered_user: dict, user_payload: dict):
    response = await client.post("/auth/register", json=user_payload)

    assert response.status_code == 409


async def test_register_short_password(client: AsyncClient):
    response = await client.post(
        "/auth/register", json={"email": "a@example.com", "password": "123"}
    )

    assert response.status_code == 422


async def test_register_ignores_role(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"email": "evil@example.com", "password": "StrongPass123", "role": "admin"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "buyer"


async def test_login_success(client: AsyncClient, registered_user: dict, user_payload: dict):
    response = await client.post(
        "/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, registered_user: dict, user_payload: dict):
    response = await client.post(
        "/auth/login",
        data={"username": user_payload["email"], "password": "WrongPassword"},
    )

    assert response.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    response = await client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "whatever123"}
    )

    assert response.status_code == 401


async def test_me_with_access_token(client: AsyncClient, auth_headers: dict, user_payload: dict):
    response = await client.get("/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == user_payload["email"]


async def test_me_without_token(client: AsyncClient):
    response = await client.get("/users/me")

    assert response.status_code == 401


async def test_me_rejects_refresh_token(client: AsyncClient, tokens: dict):
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}

    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 401


async def test_refresh_returns_new_tokens(client: AsyncClient, tokens: dict):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, tokens: dict):
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401