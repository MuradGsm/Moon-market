import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.orders.dependencies import OrderServiceDep
from app.orders.schemas import OrderCreate, OrderFilters, OrderList, OrderRead
from app.users.dependencies import CurrentUser

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, user: CurrentUser, service: OrderServiceDep):
    return await service.create(user, data)


@router.get("", response_model=OrderList)
async def list_my_orders(
    filters: Annotated[OrderFilters, Query()], user: CurrentUser, service: OrderServiceDep
):
    return await service.list(user, filters)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: uuid.UUID, user: CurrentUser, service: OrderServiceDep):
    return await service.get(user, order_id)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(order_id: uuid.UUID, user: CurrentUser, service: OrderServiceDep):
    return await service.cancel(user, order_id)