import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
 
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
 
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Price = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
 
 
class ProductCreate(BaseModel):
    title: Title
    description: str | None = Field(default=None, max_length=5000)
    price: Price
    stock: int = Field(default=0, ge=0)
 
 
class ProductUpdate(BaseModel):
    """PATCH: меняем только те поля, которые пришли."""
 
    model_config = ConfigDict(extra="forbid")
 
    title: Title | None = None
    description: str | None = Field(default=None, max_length=5000)
    price: Price | None = None
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
 
    @model_validator(mode="after")
    def no_null_for_required_fields(self):
        # description можно обнулить, остальные поля в БД NOT NULL
        for name in ("title", "price", "stock", "is_active"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self
 
 
class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: uuid.UUID
    seller_id: uuid.UUID
    title: str
    description: str | None
    price: Decimal
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
 
 
class ProductFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
 
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    seller_id: uuid.UUID | None = None
    search: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ] | None = None
    sort: Literal["created_at", "price"] = "created_at"
    order: Literal["asc", "desc"] = "desc"
 
    @model_validator(mode="after")
    def check_price_range(self):
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be <= max_price")
        return self


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int