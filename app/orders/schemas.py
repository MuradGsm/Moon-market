import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.orders.models import OrderStatus

class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int =Field(ge=1, le=1000)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def no_duplicate_products(self):
        ids = [item.product_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate product_id in items")
        return self


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    product_id: uuid.UUID
    product_title: str
    unit_price: Decimal
    quantity: int


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: uuid.UUID
    buyer_id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime


class OrderFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
 
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    status: OrderStatus | None = None


class OrderList(BaseModel):
    items: list[OrderRead]
    total: int
    limit: int
    offset: int