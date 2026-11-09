from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Moon market"
    environment: Literal['local', 'test', 'prod'] = "local"
    debug: bool = False

    public_base_url: str = "http://localhost:8000"

    # Postgres
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = 'postgres'
    postgres_port: int = 5432

    # DB pool /logging
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    def _build_url(self, driver: str, db_name: str | None = None) -> str:
        return URL.create(
            drivername=driver,
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=db_name or self.postgres_db, 
        ).render_as_string(hide_password=False)

    @property
    def database_url(self) -> str:
        return self._build_url("postgresql+asyncpg")

    @property
    def alembic_database_url(self) -> str:
        return self._build_url("postgresql+psycopg2")


    @property
    def test_database_url(self) -> str:
        return self._build_url("postgresql+asyncpg", f"{self.postgres_db}_test")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()