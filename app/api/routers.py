from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_superuser

transactions_router = APIRouter(prefix="/endpoint/v1/transactions", tags=["transactions"])
users_router = APIRouter(prefix="/api/v1/profile", tags=["me"])
analysis_router = APIRouter(prefix="/endpoint/v1", tags=["analysis"])
auth_router = APIRouter(prefix="/endpoint/v1/auth", tags=["authentication"])
admin_router = APIRouter(
    prefix="/endpoint/v1/admin_panel", tags=["admin"], dependencies=[Depends(get_current_superuser)]
)

from app.api.v1 import user_endpoints, admin_endpoints, analysis_endpoints, auth_endpoints, transaction_endpoint # noqa
