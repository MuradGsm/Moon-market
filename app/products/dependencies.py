from typing import Annotated
 
from fastapi import Depends
 
from app.core.database import DbSession
from app.core.redis import RedisDep
from app.products.cache import ProductCache
from app.products.service import ProductService
from app.users.dependencies import require_role
from app.users.models import User, UserRole
 
 
def get_product_cache(redis: RedisDep) -> ProductCache:
    return ProductCache(redis)
 
 
ProductCacheDep = Annotated[ProductCache, Depends(get_product_cache)]
 
 
def get_product_service(db: DbSession, cache: ProductCacheDep) -> ProductService:
    return ProductService(db, cache)
 
 
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
 
# RBAC: только продавец или админ
SellerOrAdmin = Annotated[User, Depends(require_role(UserRole.SELLER, UserRole.ADMIN))]