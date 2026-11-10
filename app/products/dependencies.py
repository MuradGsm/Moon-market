from typing import Annotated

from fastapi import Depends

from app.core.database import DbSession
from app.products.service import ProductService
from app.users.dependencies import require_role
from app.users.models import User, UserRole


def get_product_service(db: DbSession) -> ProductService:
    return ProductService(db)

ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]

SellerOrAdmin = Annotated[User, Depends(require_role(UserRole.SELLER, UserRole.ADMIN))]

