from fastapi import APIRouter

transactions_router = APIRouter(prefix="/endpoints/v1/transactions", tags=["transactions"])
users_router = APIRouter(prefix="/endpoints/v1/users", tags=["users"])
analysis_router = APIRouter(prefix="/endpoints/v1", tags=["analysis"])