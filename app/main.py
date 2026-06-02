import typing
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.endpoints.routers import admin_router, analysis_router, auth_router, transactions_router, users_router



@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None]:
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(transactions_router)
app.include_router(users_router)
app.include_router(analysis_router)
app.include_router(auth_router)
app.include_router(admin_router)
