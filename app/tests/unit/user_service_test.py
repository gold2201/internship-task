from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.enums import UserStatusEnum
from app.exceptions.exceptions import (
    BadRequestDataException,
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserAlreadyExistsException,
    UserNotExistsException,
)
from app.services.user_services import UserService


class TestGetAllUsersService:
    @pytest.mark.asyncio
    async def test_returns_users(self, user_repo, balance_repo):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        expected_users = [object(), object()]
        user_repo.get_all_users.return_value = expected_users

        result = await service.get_all_users()

        assert result == expected_users
        user_repo.get_all_users.assert_awaited_once()


class TestCreateUserService:
    @pytest.mark.asyncio
    async def test_empty_email_raises(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)

        with pytest.raises(BadRequestDataException):
            await service.create_user(
                email="   ",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_already_exists_raises(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        user_repo.get_by_email.return_value = object()

        with pytest.raises(UserAlreadyExistsException):
            await service.create_user(
                email="test@test.com",
                session=session,
            )

        user_repo.get_by_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        user_repo.get_by_email.return_value = None

        test_uuid = uuid4()

        def add_user(user):
            user.id = test_uuid

        user_repo.add.side_effect = add_user
        user_repo.get_by_id.return_value = object()

        result = await service.create_user(
            email="test@test.com",
            session=session,
        )

        user_repo.add.assert_called_once()
        balance_repo.add_many.assert_called_once()

        session.flush.assert_awaited_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()

        assert result is not None


class TestUpdateUserStatusService:
    @pytest.mark.asyncio
    async def test_user_not_found_raises(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotExistsException):
            await service.update_status(
                user_id=uuid4(),
                new_status=UserStatusEnum.ACTIVE,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_already_blocked_raises(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        user = MagicMock()
        user.status = UserStatusEnum.BLOCKED
        user_repo.get_by_id.return_value = user

        with pytest.raises(UserAlreadyBlockedException):
            await service.update_status(
                user_id=uuid4(),
                new_status=UserStatusEnum.BLOCKED,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_already_active_raises(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        user = MagicMock()
        user.status = UserStatusEnum.ACTIVE
        user_repo.get_by_id.return_value = user

        with pytest.raises(UserAlreadyActiveException):
            await service.update_status(
                user_id=uuid4(),
                new_status=UserStatusEnum.ACTIVE,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_success(self, user_repo, balance_repo, session):
        service = UserService(user_repo=user_repo, balance_repo=balance_repo)
        user = MagicMock()
        user.status = UserStatusEnum.ACTIVE
        user_repo.get_by_id.return_value = user
        user_repo.update_status.return_value = user

        result = await service.update_status(
            user_id=uuid4(),
            new_status=UserStatusEnum.BLOCKED,
            session=session,
        )

        user_repo.update_status.assert_awaited_once()
        session.commit.assert_awaited_once()
        assert result == user
