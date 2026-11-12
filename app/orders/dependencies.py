from typing import Annotated

from fastapi import Depends

from app.core.database import DbSession
from app.orders.service import OrderService
from app.orders.uow import UnitOfWork
from app.products.dependencies import ProductCacheDep


def get_uow(db: DbSession) -> UnitOfWork:
    return UnitOfWork(db)


UowDep = Annotated[UnitOfWork, Depends(get_uow)]


def get_order_service(uow: UowDep, cache: ProductCacheDep) -> OrderService:
    return OrderService(uow, cache)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]