from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import oauth2_scheme
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import db_manager
from app.endpoints.routers import auth_router
from app.models.db_models import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.token import Token
from app.schemas.user import RequestUserModel, ResponseUserModel


@auth_router.post("/sign_up", response_model=ResponseUserModel)
async def sign_up(
    user_data: RequestUserModel,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> User:
    user_repo = UserRepository(session)

    existing_user = await user_repo.get_by_email(user_data.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = await user_repo.create(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )

    return new_user


@auth_router.post("/sign_in", response_model=Token)
async def sign_in(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> dict:
    user_repo = UserRepository(session)
    token_repo = TokenRepository(session)

    user = await user_repo.get_by_email(form_data.username)

    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    payload = decode_token(refresh_token_str)
    expires_at = datetime.fromtimestamp(payload["exp"]) if payload else datetime.now()

    await token_repo.save_refresh_token(
        token=refresh_token_str,
        user_id=int(user.id),
        expires_at=expires_at,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
    }


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token_value: str,
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> dict:
    user_repo = UserRepository(session)
    token_repo = TokenRepository(session)

    payload = decode_token(refresh_token_value)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Refresh token required",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        ) from err

    refresh_record = await token_repo.get_valid_refresh_token(refresh_token_value, user_id)

    if not refresh_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
        )

    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    new_payload = decode_token(new_refresh_token)
    new_expires_at = datetime.fromtimestamp(new_payload["exp"]) if new_payload else datetime.now()

    await token_repo.save_and_revoke(
        old_token=refresh_record,
        new_token_str=new_refresh_token,
        user_id=int(user.id),
        expires_at=new_expires_at,
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@auth_router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> dict:
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError) as err:
        raise HTTPException(status_code=401, detail="Invalid user ID") from err

    token_repo = TokenRepository(session)
    await token_repo.revoke_all_user_tokens(user_id)

    return {"detail": "Logged out successfully"}
