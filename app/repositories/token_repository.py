from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import RefreshToken


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_refresh_token(self, token: str, user_id: int, expires_at: datetime) -> RefreshToken:
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        await self.session.commit()
        return refresh_token

    async def get_valid_refresh_token(self, token: str, user_id: int) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked = datetime.now()  # type: ignore[assignment]
        await self.session.commit()

    async def save_and_revoke(
        self,
        old_token: RefreshToken,
        new_token_str: str,
        user_id: int,
        expires_at: datetime,
    ) -> RefreshToken:
        old_token.revoked = datetime.now()  # type: ignore[assignment]
        new_token = RefreshToken(
            token=new_token_str,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.session.add(new_token)
        await self.session.commit()
        return new_token

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(None))
            .values(revoked=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()
