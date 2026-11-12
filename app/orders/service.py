import uuid
from decimal import Decimal

from app.core.exceptions import (
    CannotBuyOwnProduct,
    InsufficientStock,
    InvalidOrderState,
    OrderNotFound,
    ProductNotAvailable,
)
from app.orders.models import Order, OrderStatus
from app.orders.schemas import OrderCreate, OrderFilters, OrderList, OrderRead
from app.orders.uow import UnitOfWork
from app.products.cache import ProductCache
from app.users.models import User, UserRole


class OrderService:

    def __init__(self, uow: UnitOfWork, cache: ProductCache):
        self.uow = uow
        self.cache = cache

    async def create(self, user: User, data: OrderCreate) -> Order:
        async with self.uow as uow:
            ids = [item.product_id for item in data.items]
            products = await uow.products.get_many_for_update(ids)
            by_id = {p.id: p for p in products}


            lines: list[dict] = []
            total = Decimal("0")
            for item in data.items:
                product = by_id.get(item.product_id)
                if product is None or not product.is_active:
                    raise ProductNotAvailable(item.product_id)
                if product.seller_id == user.id:
                    raise CannotBuyOwnProduct()
                if product.stock < item.quantity:
                    raise InsufficientStock(product.id, product.stock)

                product.stock -= item.quantity
                total += product.price * item.quantity
                lines.append(
                    {
                        "product_id": product.id,
                        "product_title": product.title, 
                        "unit_price": product.price,
                        "quantity": item.quantity,
                    }
                )
            order = await uow.orders.create(user.id, total, lines)
            await uow.commit()
            
        await self.cache.invalidate()
        return order

    async def get(self, user: User, order_id: uuid.UUID) -> Order:
        order = await self.uow.orders.get_by_id(order_id)
        if order is None or (order.buyer_id != user.id and user.role != UserRole.ADMIN):
            raise OrderNotFound()
        return order

    async def list(self, user: User, filters: OrderFilters) -> OrderList:
        orders = await self.uow.orders.list_for_buyer(user.id, filters)
        total = await self.uow.orders.count_for_buyer(user.id, filters)
        return OrderList(
            items=[OrderRead.model_validate(o) for o in orders],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def cancel(self, user: User, order_id: uuid.UUID) -> Order:
        async with self.uow as uow:
            order = await uow.orders.get_by_id(order_id, for_update=True)
            if order is None or (order.buyer_id != user.id and user.role != UserRole.ADMIN):
                raise OrderNotFound()
            if order.status != OrderStatus.PENDING:
                raise InvalidOrderState(order.status.value)

            products = await uow.products.get_many_for_update(
                [item.product_id for item in order.items]
            )
            by_id = {p.id: p for p in products}
            for item in order.items:
                by_id[item.product_id].stock += item.quantity

            await uow.orders.set_status(order, OrderStatus.CANCELLED)
            await uow.commit()

        await self.cache.invalidate()
        return order