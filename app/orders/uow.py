from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.repository import OrderRepository
from app.products.repository import ProductRepository


class UnitOfWork:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.orders = OrderRepository(session)
        self.products = ProductRepository(session)

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.session.rollback()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()