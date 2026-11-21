"""端末アクセストークンの発行と検証処理を提供する。"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.custom_exception import UnauthorizedException


class DeviceAuthUtil:
    """端末用のJWTアクセストークンを発行・検証する。

    Args:
        なし。

    Returns:
        端末アクセストークン用のユーティリティ。
    """

    @staticmethod
    def create_access_token(device_uuid: str, config: DeviceAuthConfig) -> str:
        """端末UUIDと有効期限を含むHS256 JWTを発行する。

        Args:
            device_uuid: 認証済み端末のUUID。
            config: 端末用の署名鍵と有効期間。

        Returns:
            署名済みのアクセストークン。
        """
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=config.access_token_expire_seconds)
        payload = {
            "sub": device_uuid,
            "device_uuid": device_uuid,
            "iat": issued_at,
            "exp": expires_at,
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, config.jwt_secret, algorithm="HS256")

    @staticmethod
    def verify_access_token(access_token: str, config: DeviceAuthConfig) -> str:
        """端末用JWTを検証し、署名済みの端末UUIDを取得する。

        Args:
            access_token: Authorizationヘッダーで受け取ったBearerトークン。
            config: 端末用の署名鍵を含む設定。

        Returns:
            トークンに含まれる検証済みの端末UUID。

        Raises:
            UnauthorizedException: 署名、有効期限、端末UUIDのいずれかが不正な場合。
        """
        try:
            payload = jwt.decode(
                access_token,
                config.jwt_secret,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "device_uuid"]},
            )
            device_uuid = payload["device_uuid"]
            if (
                type(payload["exp"]) is not int
                or not isinstance(device_uuid, str)
                or payload["sub"] != device_uuid
                or str(UUID(device_uuid)) != device_uuid.lower()
            ):
                raise UnauthorizedException()
        except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError):
            raise UnauthorizedException() from None
        return device_uuid
