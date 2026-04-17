import typing
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import db_manager
from app.endpoints.v1 import analysis, transaction, user


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None]:
    await db_manager.create_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(analysis.router)
app.include_router(transaction.router)
app.include_router(user.router)
