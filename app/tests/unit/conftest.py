import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def user_repo():
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def balance_repo():
    mock = AsyncMock()
    mock.add = MagicMock()
    mock.add_many = MagicMock()
    return mock


@pytest.fixture
def transaction_repo():
    return AsyncMock()


@pytest.fixture
def session():
    return AsyncMock()
