import uuid
from collections.abc import Sequence

from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.products.models import Product
from app.products.schemas import ProductCreate, ProductFilters


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _apply_filter(stmt: Select, filters: ProductFilters) -> Select:
        stmt = stmt.where(Product.is_active.is_(True))
        if filters.min_price is not None:
            stmt = stmt.where(Product.price >= filters.min_price)
        if filters.max_price is not None:
            stmt = stmt.where(Product.price <= filters.max_price)
        if filters.seller_id is not None:
            stmt = stmt.where(Product.seller_id == filters.seller_id)
        return stmt

    async def create(self, seller_id: uuid.UUID, data: ProductCreate) -> Product:
        product = Product(seller_id=seller_id, **data.model_dump())
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        return await self.session.get(Product, product_id)

    async def list(self, filters: ProductFilters) -> Sequence[Product]:
        column = getattr(Product, filters.sort)
        direction = column.desc() if filters.order == "desc" else column.asc()
        stmt = (
            self._apply_filter(select(Product), filters)
            .order_by(direction, Product.id)
            .limit(filters.limit)
            .offset(filters.offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, filters: ProductFilters) -> int:
        stmt = self._apply_filter(select(func.count()).select_from(Product), filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, product: Product, values: dict) -> Product:
        for field, value in values.items():
            setattr(product, field, value)
        await self.session.flush()
        await self.session.refresh(product)
        return product