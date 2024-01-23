import asyncio
from typing import Any, AsyncGenerator, Generator

import pytest
from httpx import AsyncClient

from src.main import app

pytest_plugins = [
    "tests.fixtures",
]


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def client() -> AsyncGenerator[AsyncClient, None]:
    # note about base_url change it to your required location
    async with AsyncClient(app=app, base_url="") as client:
        yield client
