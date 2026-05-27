from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import CurrencyEnum, UserStatusEnum
from app.models.db_models import User, UserBalance


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


async def create_user_with_balances(
    session: AsyncSession,
    email: str | None = None,
    status: UserStatusEnum | str = UserStatusEnum.ACTIVE,
    hashed_password: str = "superpassword",
    user_id: UUID | None = None,
) -> User:
    email = email or f"user-{uuid4().hex}@test.com"

    user = User(
        id=user_id or uuid4(),
        email=email,
        status=_enum_value(status),
        hashed_password=hashed_password,
    )
    session.add(user)
    await session.flush()

    balances = [
        UserBalance(
            user_id=user.id,
            currency=_enum_value(currency),
            amount=0,
        )
        for currency in CurrencyEnum
    ]
    session.add_all(balances)

    await session.commit()
    await session.refresh(user)
    return user
