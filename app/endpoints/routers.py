from fastapi import APIRouter

transactions_router = APIRouter(prefix="/endpoint/v1/transactions", tags=["transactions"])
users_router = APIRouter(prefix="/endpoint/v1/users", tags=["users"])
analysis_router = APIRouter(prefix="/endpoint/v1", tags=["analysis"])
auth_router = APIRouter(prefix="/endpoints/auth", tags=["authentication"])
