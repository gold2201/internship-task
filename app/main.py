import os
import typing
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, status
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models.db_models import Base, Transaction, User, UserBalance
from app.exceptions.exceptions import (
    BadRequestDataException,
    CreateTransactionForBlockedUserException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
    UpdateTransactionForBlockedUserException,
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserAlreadyExistsException,
    UserNotExistsException,
)
from app.schemas.python_models import (
    CurrencyEnum,
    RequestTransactionModel,
    RequestUserModel,
    RequestUserUpdateModel,
    ResponseUserBalanceModel,
    ResponseUserModel,
    TransactionModel,
    TransactionStatusEnum,
    UserModel,
    UserStatusEnum,
)
from app.services.queries import (
    get_not_rollbacked_deposit_amount,
    get_not_rollbacked_transactions_count,
    get_not_rollbacked_withdraw_amount,
    get_registered_and_deposit_users_count,
    get_registered_and_not_rollbacked_deposit_users_count,
    get_registered_users_count,
    get_transactions_count,
)

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> typing.AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None]:
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/users", response_model=list[ResponseUserModel] | None, status_code=status.HTTP_200_OK)
async def get_users(
    user_id: int | None = None,
    email: str | None = None,
    user_status: str | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[ResponseUserModel]:
    q = select(User).order_by(User.created.desc())
    if user_id is not None:
        q = q.where(User.id == user_id)
    if email is not None:
        q = q.where(User.email == email)
    if user_status is not None:
        q = q.where(User.status == user_status)
    users = await session.scalars(q)
    results = []
    for user in users:
        result = ResponseUserModel(
            id=int(user.id),
            email=str(user.email),
            status=UserStatusEnum(str(user.status)),
            created=typing.cast(datetime, user.created),
        )

        balances_result = await session.execute(select(UserBalance).where(UserBalance.user_id == user.id))

        balances = balances_result.scalars().all()

        result.balances = [
            ResponseUserBalanceModel(currency=CurrencyEnum(str(b.currency)), amount=float(b.amount)) for b in balances
        ]

        results.append(result)

    return sorted(results, key=lambda x: x.created or datetime.min)


@app.post("/users", status_code=status.HTTP_200_OK)
async def post_user(user: RequestUserModel, session: AsyncSession = Depends(get_async_session)) -> UserModel:
    email = user.email.strip()
    email = "".join([x for x in email if x != " "])
    if len(email) == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email can't consist entirely of spaces"
        )

    check_result = await session.execute(select(User).where(User.email == email))
    existing_user = check_result.scalar()

    if existing_user:
        raise UserAlreadyExistsException(
            status_code=status.HTTP_409_CONFLICT, detail=f"User with email=`{email}` already exists"
        )

    db_user = User(email=email, status="ACTIVE", created=datetime.now())
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    currencies = list({str(x) for x in CurrencyEnum})
    for currency in currencies:
        user_balance = UserBalance(user_id=db_user.id, currency=currency, amount=0, created=datetime.now())
        session.add(user_balance)

    await session.commit()

    result = await session.execute(select(User).where(User.email == email))
    created_user = result.scalar_one()

    return UserModel.model_validate(created_user)


@app.patch("/users/{user_id}", response_model=list[UserModel] | None)
async def patch_user(
    user_id: int, user: RequestUserUpdateModel, session: AsyncSession = Depends(get_async_session)
) -> UserModel:
    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )

    db_user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = db_user_result.scalar()

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id=`{user_id}` does not exist"
        )

    if db_user.status == "BLOCKED" and user.status == "BLOCKED":
        raise UserAlreadyBlockedException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is already blocked"
        )

    if db_user.status == "ACTIVE" and user.status == "ACTIVE":
        raise UserAlreadyActiveException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is already active"
        )

    await session.execute(update(User).values(status=user.status).where(User.id == user_id))
    await session.commit()

    updated_user_result = await session.execute(select(User).where(User.id == user_id))
    updated_user = updated_user_result.scalar_one()

    return UserModel.model_validate(updated_user)


@app.get("/transactions", response_model=list[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def get_transactions(
    user_id: int | None = None, session: AsyncSession = Depends(get_async_session)
) -> list[TransactionModel]:
    q = select(Transaction).order_by(Transaction.created.desc())
    if user_id is not None:
        q = q.where(Transaction.user_id == user_id)

    result = await session.execute(q)
    transactions = result.scalars().all()

    results: list[TransactionModel] = []
    for t in transactions:
        transaction_model = TransactionModel(
            id=int(t.id),
            user_id=int(t.user_id),
            currency=CurrencyEnum(str(t.currency)),
            amount=float(t.amount),
            status=TransactionStatusEnum(str(t.status)),
            created=typing.cast(datetime, t.created),
        )
        results.append(transaction_model)

    return results


@app.post("/{user_id}/transactions", response_model=list[TransactionModel] | None, status_code=status.HTTP_200_OK)
async def post_transaction(
    user_id: int, transaction: RequestTransactionModel, session: AsyncSession = Depends(get_async_session)
) -> TransactionModel:
    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )

    if transaction.currency not in {str(x) for x in CurrencyEnum}:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Currency does not exist"
        )

    if transaction.amount == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Transaction can not have zero amount"
        )

    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar()

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id=`{user_id}` does not exist"
        )

    if str(db_user.status) != "ACTIVE":
        raise CreateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is blocked"
        )

    balance_result = await session.execute(
        select(UserBalance).where((UserBalance.user_id == user_id) & (UserBalance.currency == transaction.currency))
    )
    db_user_balance = balance_result.scalar()

    if not db_user_balance:
        raise BadRequestDataException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Balance for currency `{transaction.currency}` not found"
        )

    if float(db_user_balance.amount) + transaction.amount < 0:
        raise NegativeBalanceException(status_code=status.HTTP_400_BAD_REQUEST, detail="Negative balance")

    current_amount = float(db_user_balance.amount)
    new_amount = current_amount + transaction.amount

    await session.execute(update(UserBalance).values(amount=new_amount).where(UserBalance.id == db_user_balance.id))

    transaction_result = await session.execute(
        insert(Transaction)
        .values(
            user_id=int(db_user.id),
            currency=transaction.currency,
            amount=transaction.amount,
            status="PROCESSED",
            created=datetime.now(),
        )
        .returning(Transaction)
    )
    await session.commit()

    created_transaction = transaction_result.scalar_one()

    return TransactionModel.model_validate(created_transaction)


@app.patch("/{user_id}/transactions/{transaction_id}", response_model=TransactionModel)
async def patch_rollback_transaction(
    user_id: int, transaction_id: int, session: AsyncSession = Depends(get_async_session)
) -> TransactionModel:
    if user_id < 0 or transaction_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unprocessable data in request"
        )

    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar()

    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id=`{user_id}` does not exist"
        )

    transaction_result = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    db_transaction = transaction_result.scalar()

    if not db_transaction:
        raise TransactionNotExistsException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Transaction with id=`{transaction_id}` does not exist"
        )

    if int(db_transaction.user_id) != int(db_user.id):
        raise TransactionDoesNotBelongToUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction with id=`{transaction_id}` does not belong to user with id=`{user_id}`",
        )

    if str(db_transaction.status) == "ROLLBACKED":
        raise TransactionAlreadyRollbackedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction with id=`{transaction_id}` is already rollbacked",
        )

    if str(db_user.status) == "BLOCKED":
        raise UpdateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with id=`{user_id}` is blocked"
        )

    balance_result = await session.execute(
        select(UserBalance).where((UserBalance.user_id == user_id) & (UserBalance.currency == db_transaction.currency))
    )
    db_user_balance = balance_result.scalar()

    if not db_user_balance:
        raise BadRequestDataException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Balance for currency `{db_transaction.currency}` not found"
        )

    current_amount = float(db_user_balance.amount)
    transaction_amount = float(db_transaction.amount)

    if transaction_amount < 0:
        new_amount = current_amount + abs(transaction_amount)
    else:
        new_amount = current_amount - transaction_amount

    if new_amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Negative balance: {new_amount}"
        )

    await session.execute(update(UserBalance).values(amount=new_amount).where(UserBalance.id == db_user_balance.id))

    updated_transaction_result = await session.execute(
        update(Transaction)
        .values(status="ROLLBACKED", updated=datetime.now())
        .where(Transaction.id == transaction_id)
        .returning(Transaction)
    )
    await session.commit()

    updated_transaction = updated_transaction_result.scalar_one()

    return TransactionModel.model_validate(updated_transaction)


@app.get("/transactions/analysis", response_model=list[dict[str, typing.Any]], status_code=status.HTTP_200_OK)
async def get_transaction_analysis(session: AsyncSession = Depends(get_async_session)) -> list[dict[str, typing.Any]]:
    dt_gt: date = datetime.now().date() - timedelta(weeks=1) + timedelta(days=1)
    dt_lt: date = datetime.now().date()
    results: list[dict[str, typing.Any]] = []

    for _ in range(52):
        registered_users_count = int(await get_registered_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt))
        registered_and_deposit_users_count = int(
            await get_registered_and_deposit_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        registered_and_not_rollbacked_deposit_users_count = int(
            await get_registered_and_not_rollbacked_deposit_users_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        not_rollbacked_deposit_amount = float(
            await get_not_rollbacked_deposit_amount(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        not_rollbacked_withdraw_amount = float(
            await get_not_rollbacked_withdraw_amount(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )
        transactions_count = int(await get_transactions_count(session, dt_gt=dt_gt, dt_lt=dt_lt))
        not_rollbacked_transactions_count = int(
            await get_not_rollbacked_transactions_count(session, dt_gt=dt_gt, dt_lt=dt_lt)
        )

        result = {
            "start_date": dt_gt.isoformat(),
            "end_date": dt_lt.isoformat(),
            "registered_users_count": registered_users_count,
            "registered_and_deposit_users_count": registered_and_deposit_users_count,
            "registered_and_not_rollbacked_deposit_users_count": registered_and_not_rollbacked_deposit_users_count,
            "not_rollbacked_deposit_amount": not_rollbacked_deposit_amount,
            "not_rollbacked_withdraw_amount": not_rollbacked_withdraw_amount,
            "transactions_count": transactions_count,
            "not_rollbacked_transactions_count": not_rollbacked_transactions_count,
        }

        has_data = any(
            result[field] > 0 # type: ignore[operator]
            for field in (
                "registered_users_count",
                "registered_and_deposit_users_count",
                "registered_and_not_rollbacked_deposit_users_count",
                "not_rollbacked_deposit_amount",
                "not_rollbacked_withdraw_amount",
                "transactions_count",
                "not_rollbacked_transactions_count",
            )
        )

        if has_data:
            results.append(result)

        dt_gt -= timedelta(weeks=1)
        dt_lt -= timedelta(weeks=1)
    return results
