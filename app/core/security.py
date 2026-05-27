from datetime import datetime, timedelta

import bcrypt
from jose import jwt

from app.core.settings import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode()[:72], hashed_password.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    return jwt.encode(
        to_encode,
        str(settings.SECRET_KEY),
        algorithm=str(settings.ALGORITHM),
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    return jwt.encode(
        to_encode,
        str(settings.SECRET_KEY),
        algorithm=str(settings.ALGORITHM),
    )


def decode_token(token: str) -> dict | None:
    return jwt.decode(
        token,
        str(settings.SECRET_KEY),
        algorithms=[str(settings.ALGORITHM)],
    )
