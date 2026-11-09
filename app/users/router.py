from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.users.dependencies import CurrentUser, UserServiceDep
from app.users.schemas import RefreshRequest, Token, UserCreate, UserRead

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


@auth_router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: UserServiceDep):
    return await service.register(data)


@auth_router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: UserServiceDep
):
    return await service.authenticate(form.username, form.password)  # username = email


@auth_router.post("/refresh", response_model=Token)
async def refresh(data: RefreshRequest, service: UserServiceDep):
    return await service.refresh(data.refresh_token)


@users_router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user