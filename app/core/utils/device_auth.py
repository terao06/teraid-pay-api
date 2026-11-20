"""端末アクセストークンの発行処理を提供する。"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.core.config.device_auth import DeviceAuthConfig


class DeviceAuthUtil:
    """認証済み端末のJWTアクセストークンを発行する。

    Args:
        なし。

    Returns:
        端末アクセストークン発行用のユーティリティ。
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
