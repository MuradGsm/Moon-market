import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.products.dependencies import ProductServiceDep, SellerOrAdmin
from app.products.schemas import (
    ProductCreate, ProductRead, ProductList, ProductFilters, ProductUpdate
)


router = APIRouter(prefix='/products', tags=['products'])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, user: SellerOrAdmin, service: ProductServiceDep):
    return await service.create(user, data)


@router.get("", response_model=ProductList)
async def list_products(
    filters: Annotated[ProductFilters, Query()], service: ProductServiceDep
):
    return await service.list(filters)

@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: uuid.UUID, service: ProductServiceDep):
    return await service.get(product_id)

@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    user: SellerOrAdmin,
    service: ProductServiceDep,
):
    return await service.update(user, product_id, data)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: uuid.UUID, user: SellerOrAdmin, service: ProductServiceDep):
    await service.delete(user, product_id)