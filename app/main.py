import typing
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.endpoints.routers import transactions_router, users_router, analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None]:
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(transactions_router)
app.include_router(users_router)
app.include_router(analysis_router)
