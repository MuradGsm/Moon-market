import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.products.schemas import ProductFilters, ProductList

logger = logging.getLogger(__name__)


class ProductCache:

    VERSION_KEY = "products:version"

    def __init__(self, redis: Redis, ttl_seconds: int = 60):
        self.redis = redis
        self.ttl = ttl_seconds

    async def list_key(self, filters: ProductFilters) -> str:
        try:
            version = await self.redis.get(self.VERSION_KEY) or  "0"
        except RedisError:
            logger.warning("Redis unavailable, prodcts cache skipped", exc_info=True)
            return None
        digest = hashlib.sha256(str(filters.model_dump_json()).encode()).hexdigest()
        return f"products:list:v{version}:{digest}"

    async def get_list(self, key: str | None) -> ProductList | None:
        if key is None:
            return None
        try:
            raw = await self.redis.get(key)
            return ProductList.model_validate_json(raw) if raw else None
        except (RedisError, ValueError):
            logger.warning("Product cache read failed", exc_info=True)
            return None

    async def set_list(self, key: str | None, value: ProductList) -> None:
        if key is None:
            return
        try:
            await self.redis.setex(key, self.ttl, value.model_dump_json())
        except RedisError:
            logger.warning("Product cache write failed", exc_info=True)

    async def invalidate(self) -> None:
        try:
            await self.redis.incr(self.VERSION_KEY)
        except RedisError:
            logger.warning("Product cache invalidate failed", exc_info=True)