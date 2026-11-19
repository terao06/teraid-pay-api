"""店舗管理者のBearer JWTを検証し、現在の認証状態を確認する。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NoReturn

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError

from app.core.config.store_manager_auth import get_store_manager_auth_config
from app.middlewares.transaction import get_mysql_db
from app.core.exceptions.custom_exception import CustomHttpException
from app.core.exceptions.message import SERVER_ERROR, VERIFY_ERROR
from app.repositories.mysql.store_manager_repository import StoreManagerRepository


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class StoreManagerTokenClaims:
    """管理者認証とログアウトに必要な検証済みJWTクレームを保持する。

    Args:
        store_manager_id: JWTに記録された店舗管理者ID。
        roll_id: JWTに記録されたロールID。
        jti: JWTの一意な識別子。
        expires_at: JWTの有効期限（タイムゾーン情報を付けないUTC）。

    Returns:
        検証済みクレームのインスタンス。
    """

    store_manager_id: int
    roll_id: int
    jti: str
    expires_at: datetime


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
    """Bearer認証の失敗を共通形式の401応答に変換する。"""
    raise CustomHttpException.get_http_exception(
        status_code=401,
        message=VERIFY_ERROR,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_integer_claim(payload: dict, claim_name: str) -> int:
    """真偽値を除外し、整数のクレームを取得する。"""
    value = payload.get(claim_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise jwt.InvalidTokenError(f"Invalid {claim_name} claim")
    return value


def get_store_manager_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> StoreManagerTokenClaims:
    """署名、有効期限、必須クレームを検証し、認証に必要な値を返す。

    Args:
        credentials: Authorizationヘッダーから取得したBearer認証情報。

    Returns:
        店舗管理者ID、ロールID、JWT識別子、有効期限。

    Raises:
        HTTPException: Bearer認証情報がないか、JWTが無効な場合。
    """
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
        jti = payload["jti"]
        if not isinstance(jti, str) or not 1 <= len(jti) <= 36:
            raise jwt.InvalidTokenError("Invalid jti claim")
        expires_at = datetime.fromtimestamp(
            _get_integer_claim(payload, "exp"), timezone.utc
        ).replace(tzinfo=None)
    except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError, OSError):
        _raise_unauthorized()

    return StoreManagerTokenClaims(store_manager_id, roll_id, jti, expires_at)


def authenticate_store_manager(
    claims: StoreManagerTokenClaims = Depends(get_store_manager_token_claims),
) -> StoreManagerAuthContext:
    """失効状態と店舗管理者の現在の状態を確認する。

    Args:
        claims: 署名と有効期限を検証済みのJWTクレーム。

    Returns:
        認証済みの店舗管理者情報。

    Raises:
        HTTPException: JWTが失効済み、管理者が無効、またはDBの参照に失敗した場合。
    """
    repository = StoreManagerRepository()
    try:
        with get_mysql_db().get_session() as mysql_session:
            if repository.is_access_token_revoked(mysql_session=mysql_session, jti=claims.jti):
                _raise_unauthorized()
            store_manager = repository.get_store_manager_by_id(
                mysql_session=mysql_session,
                store_manager_id=claims.store_manager_id,
            )
    except SQLAlchemyError:
        raise CustomHttpException.get_http_exception(
            status_code=500, message=SERVER_ERROR
        ) from None

    if (
        store_manager is None
        or not store_manager.is_active
        or store_manager.roll_id != claims.roll_id
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
