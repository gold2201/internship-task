from unittest.mock import AsyncMock, MagicMock

import pytest

from app.enums import UserStatusEnum
from app.tests.unit.transaction_service_test import make_balance, make_user


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


@pytest.fixture
def active_user(user_repo):
    user = make_user(UserStatusEnum.ACTIVE)
    user_repo.get_by_id.return_value = user
    return user


@pytest.fixture
def existing_balance(balance_repo):
    balance = make_balance(amount=100.0)
    balance_repo.get_by_user_and_currency.return_value = balance
    return balance
