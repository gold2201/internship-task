from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import db_manager
from app.enums import UserStatusEnum
from app.models.db_models import User
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_balance_repository import UserBalanceRepository
from app.repositories.user_repository import UserRepository
from app.services.transaction_service import TransactionService
from app.services.user_services import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/endpoints/auth/sign_in")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> User:
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type. Access token required",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        ) from err

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_user_repository(session: AsyncSession = Depends(db_manager.get_async_session)) -> UserRepository:
    return UserRepository(session)


async def get_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status != UserStatusEnum.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User with id={current_user.id} is blocked",
        )
    return current_user


async def get_balance_repository(
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> UserBalanceRepository:
    return UserBalanceRepository(session)


async def get_transaction_repository(
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> TransactionRepository:
    return TransactionRepository(session)


async def get_user_service(
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> UserService:
    user_repo = UserRepository(session)
    balance_repo = UserBalanceRepository(session)
    return UserService(user_repo, balance_repo)


async def get_transaction_service(
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> TransactionService:
    transaction_repo = TransactionRepository(session)
    balance_repo = UserBalanceRepository(session)
    return TransactionService(transaction_repo, balance_repo)
