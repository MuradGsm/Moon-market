import uuid
 
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.core.exceptions import PermissionDenied, ProductNotFound
from app.products.cache import ProductCache
from app.products.models import Product
from app.products.repository import ProductRepository
from app.products.schemas import (
    ProductCreate,
    ProductFilters,
    ProductList,
    ProductRead,
    ProductUpdate,
)
from app.users.models import User, UserRole
 
 
class ProductService:
 
    def __init__(self, session: AsyncSession, cache: ProductCache):
        self.session = session
        self.repo = ProductRepository(session)
        self.cache = cache
 
    async def create(self, user: User, data: ProductCreate) -> Product:
        product = await self.repo.create(user.id, data)
        await self.session.commit()
        await self.cache.invalidate() 
        return product
 
    async def get(self, product_id: uuid.UUID) -> Product:
        product = await self.repo.get_by_id(product_id)
        if product is None or not product.is_active:
            raise ProductNotFound()
        return product
 
    async def list(self, filters: ProductFilters) -> ProductList:
        key = await self.cache.list_key(filters)
        cached = await self.cache.get_list(key)
        if cached is not None:
            return cached
 
        items = await self.repo.list(filters)
        total = await self.repo.count(filters)
        result = ProductList(
            items=[ProductRead.model_validate(p) for p in items],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )
        await self.cache.set_list(key, result)
        return result
 
    async def update(self, user: User, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        product = await self._get_owned(user, product_id)
        product = await self.repo.update(product, data.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.cache.invalidate()
        return product
 
    async def delete(self, user: User, product_id: uuid.UUID) -> None:
        product = await self._get_owned(user, product_id)
        await self.repo.update(product, {"is_active": False})
        await self.session.commit()
        await self.cache.invalidate()
 
    async def _get_owned(self, user: User, product_id: uuid.UUID) -> Product:
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound()
        if product.seller_id != user.id and user.role != UserRole.ADMIN:
            raise PermissionDenied()
        return product
 