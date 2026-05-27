from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.routers import auth_router
from app.core.dependencies import get_auth_service, oauth2_scheme
from app.schemas.token import Token
from app.schemas.user import RequestUserModel, ResponseUserModel
from app.services.auth_service import AuthService


@auth_router.post("/sign_up", response_model=ResponseUserModel)
async def sign_up(
    user_data: RequestUserModel,
    service: AuthService = Depends(get_auth_service),
) -> ResponseUserModel:
    return await service.sign_up(
        email=user_data.email,
        password=user_data.password,
    )


@auth_router.post("/sign_in", response_model=Token)
async def sign_in(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    return await service.sign_in(
        email=form_data.username,
        password=form_data.password,
    )


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token_value: str,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    return await service.refresh_token(refresh_token_value=refresh_token_value)


@auth_router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    return await service.logout(token=token)
