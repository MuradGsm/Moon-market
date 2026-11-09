import uuid

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailAlreadyExists, InvalidCredentials, InvalidToken
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password
)
from app.users.models import User
from app.users.schemas import Token, UserCreate
from app.users.repository import UserRepository


_DUMMY_HASH = hash_password("dummy-password")


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        if await self.repo.get_by_email(data.email):
            raise EmailAlreadyExists()
        try:
            user = await self.repo.create(data.email, hash_password(data.password))
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise EmailAlreadyExists()
        return user

    async def authenticate(self, email: str, password: str) -> Token:
        user = await self.repo.get_by_email(email.lower())
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentials()
        if not verify_password(password, user.hashed_password) or not user.is_active:
            raise InvalidCredentials()
        return self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> Token:
        user = await self._user_from_token(refresh_token, 'refresh')
        return self._issue_tokens(user)

    async def get_user_from_access_token(self, token: str) -> User:
        return await self._user_from_token(token, "access")

    async def _user_from_token(self, token: str, token_type: str) -> User:
        try:
            user_id = uuid.UUID(decode_token(token, token_type))
        except (jwt.InvalidTokenError, ValueError):
            raise InvalidToken()
        user = await self.repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidToken()
        return user

    @staticmethod
    def _issue_tokens(user: User) -> Token:
        return Token(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )