import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.models import Order, OrderItem, OrderStatus
from app.orders.schemas import OrderFilters


class OrderRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _apply_filters(stmt: Select, buyer_id: uuid.UUID, filters: OrderFilters) -> Select:
        stmt = stmt.where(Order.buyer_id == buyer_id)
        if filters.status is not None:
            stmt = stmt.where(Order.status == filters.status)
        return stmt

    async def create(self, buyer_id: uuid.UUID, total: Decimal, lines: list[dict]) -> Order:
        order = Order(
            buyer_id=buyer_id,
            total_amount=total,
            status=OrderStatus.PENDING,
            items=[OrderItem(**line) for line in lines],
        )
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order, attribute_names=["created_at", "updated_at"])
        return order

    async def get_by_id(self, order_id: uuid.UUID, for_update: bool = False) -> Order | None:
        stmt = select(Order).where(Order.id == order_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_buyer(
        self, buyer_id: uuid.UUID, filters: OrderFilters
    ) -> Sequence[Order]:
        stmt = (
            self._apply_filters(select(Order), buyer_id, filters)
            .order_by(Order.created_at.desc(), Order.id)
            .limit(filters.limit)
            .offset(filters.offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_for_buyer(self, buyer_id: uuid.UUID, filters: OrderFilters) -> int:
        stmt = self._apply_filters(select(func.count()).select_from(Order), buyer_id, filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def set_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        await self.session.flush()
        await self.session.refresh(order, attribute_names=["updated_at"])
        return order