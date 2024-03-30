from redis import asyncio as aioredis
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    pass


redis_client = aioredis.from_url(
    url=settings.db_url_redis,
    db=0,
    decode_responses=True,
)
