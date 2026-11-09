from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.database import DbSession
from app.core.exceptions import PermissionDenied
from app.users.models import User, UserRole
from app.users.service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], service: UserServiceDep
) -> User:
    return await service.get_user_from_access_token(token)

CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDenied()
        return user
    return checker