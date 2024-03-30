from collections.abc import AsyncGenerator

from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.db_url_postgresql, echo=True)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:  # pragma: no cover
        yield session


redis_client = aioredis.from_url(
    url=settings.db_url_redis,
    db=0,
    decode_responses=True,
)
