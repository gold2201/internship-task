from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.db_models import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, token_repo: TokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def sign_up(self, email: str, password: str) -> User:
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        new_user = await self.user_repo.create(
            email=email,
            hashed_password=get_password_hash(password),
        )
        return new_user

    async def sign_in(self, email: str, password: str) -> dict:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, str(user.hashed_password)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token_str = create_refresh_token({"sub": str(user.id)})

        payload = decode_token(refresh_token_str)
        expires_at = datetime.fromtimestamp(payload["exp"]) if payload else datetime.now()

        await self.token_repo.save_refresh_token(
            token=refresh_token_str,
            user_id=user.id,
            expires_at=expires_at,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
        }

    async def refresh_token(self, refresh_token_value: str) -> dict:
        payload = decode_token(refresh_token_value)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        refresh_record = await self.token_repo.get_valid_refresh_token(refresh_token_value, user_id_str)
        if not refresh_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found or revoked")

        user = await self.user_repo.get_by_id(UUID(user_id_str))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        new_access_token = create_access_token({"sub": str(user.id)})
        new_refresh_token = create_refresh_token({"sub": str(user.id)})

        new_payload = decode_token(new_refresh_token)
        new_expires_at = datetime.fromtimestamp(new_payload["exp"]) if new_payload else datetime.now()

        await self.token_repo.save_and_revoke(
            old_token=refresh_record,
            new_token_str=new_refresh_token,
            user_id=user.id,
            expires_at=new_expires_at,
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, token: str) -> dict:
        payload = decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token")
        await self.token_repo.revoke_all_user_tokens(UUID(user_id_str))
        return {"detail": "Logged out successfully"}
