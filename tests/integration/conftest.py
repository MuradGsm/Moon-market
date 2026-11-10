import uuid

import pytest_asyncio
from httpx import AsyncClient

from app.products import models as product_models  # noqa: F401  (таблица products в metadata)
from app.users.models import User, UserRole

PASSWORD = "StrongPass123"


@pytest_asyncio.fixture
async def make_user(client: AsyncClient, session_factory):

    async def _make(email: str, role: UserRole = UserRole.BUYER) -> dict:
        response = await client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]

        if role != UserRole.BUYER:
            async with session_factory() as session:
                user = await session.get(User, uuid.UUID(user_id))
                user.role = role
                await session.commit()

        login = await client.post(
            "/auth/login", data={"username": email, "password": PASSWORD}
        )
        assert login.status_code == 200, login.text
        return {
            "id": user_id,
            "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
        }

    return _make


@pytest_asyncio.fixture
async def seller(make_user) -> dict:
    return await make_user("seller@example.com", UserRole.SELLER)


@pytest_asyncio.fixture
async def other_seller(make_user) -> dict:
    return await make_user("other-seller@example.com", UserRole.SELLER)


@pytest_asyncio.fixture
async def buyer(make_user) -> dict:
    return await make_user("buyer@example.com", UserRole.BUYER)


@pytest_asyncio.fixture
async def admin(make_user) -> dict:
    return await make_user("admin@example.com", UserRole.ADMIN)