from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import DbSession, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)


@app.get("/health")
async def health(request: Request, db: DbSession):
    try:
        await db.execute(text("SELECT 1"))
        await request.app.state.redis.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="unhealthy")
    return {"status": "ok"}