from dataclasses import dataclass
from typing import NoReturn

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config.store_manager_auth import get_store_manager_auth_config
from app.middlewares.transaction import get_mysql_db
from app.core.exceptions.custom_exception import CustomHttpException
from app.core.exceptions.message import VERIFY_ERROR
from app.repositories.mysql.store_manager_repository import StoreManagerRepository


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class StoreManagerAuthContext:
    """認証済み店舗管理者のユーザー情報。"""

    store_manager_id: int
    store_id: int
    name: str
    email: str
    roll_id: int
    is_active: bool


def _raise_unauthorized() -> NoReturn:
    raise CustomHttpException.get_http_exception(
        status_code=401,
        message=VERIFY_ERROR,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_integer_claim(payload: dict, claim_name: str) -> int:
    value = payload.get(claim_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise jwt.InvalidTokenError(f"Invalid {claim_name} claim")
    return value


def authenticate_store_manager(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> StoreManagerAuthContext:
    """Bearer JWTを検証し、認証済み店舗管理者情報を返す。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        _raise_unauthorized()

    auth_config = get_store_manager_auth_config()
    try:
        payload = jwt.decode(
            credentials.credentials,
            auth_config.jwt_secret,
            algorithms=["HS256"],
            options={
                "require": [
                    "sub",
                    "store_manager_id",
                    "roll_id",
                    "iat",
                    "exp",
                    "jti",
                ]
            },
        )
        store_manager_id = _get_integer_claim(payload, "store_manager_id")
        roll_id = _get_integer_claim(payload, "roll_id")
        if payload.get("sub") != str(store_manager_id):
            raise jwt.InvalidTokenError("Invalid sub claim")
    except jwt.InvalidTokenError:
        _raise_unauthorized()

    with get_mysql_db().get_session() as mysql_session:
        store_manager = StoreManagerRepository().get_store_manager_by_id(
            mysql_session=mysql_session,
            store_manager_id=store_manager_id,
        )

    if (
        store_manager is None
        or not store_manager.is_active
        or store_manager.roll_id != roll_id
    ):
        _raise_unauthorized()

    return StoreManagerAuthContext(
        store_manager_id=store_manager.store_manager_id,
        store_id=store_manager.store_id,
        name=store_manager.name,
        email=store_manager.email,
        roll_id=store_manager.roll_id,
        is_active=bool(store_manager.is_active),
    )
