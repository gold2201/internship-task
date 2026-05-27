from fastapi import Depends

from app.api.routers import users_router
from app.core.dependencies import get_active_user, get_user_service
from app.models.db_models import User
from app.schemas.user import ResponseUserBalanceModel, ResponseUserModel
from app.services.user_services import UserService


@users_router.get("", response_model=ResponseUserModel)
async def get_profile(
    current_user: User = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
) -> ResponseUserModel:
    user = await service.get_user(user_id=current_user.id)

    return user


@users_router.delete("")
async def delete_user(
    current_user: User = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
):
    await service.deactivate_user(user_id=current_user.id)
    return {"message": f"User {current_user.id} deactivated"}
