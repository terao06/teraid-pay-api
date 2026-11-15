from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from app.core.config.store_manager_auth import StoreManagerAuthConfig
from app.models.mysql.store_manager import StoreManager


class StoreManagerAuthUtil:
    """店舗管理者のパスワード検証とアクセストークン発行を行う。"""

    DUMMY_PASSWORD_HASH = (
        "$2b$12$IxwxqU2r/nreT6rtJBLFDuGDdX4hjqDXcVBI6SN65QYd9t94YpuRG"
    )

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """平文パスワードと bcrypt ハッシュを照合する。"""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (TypeError, ValueError):
            return False

    @classmethod
    def perform_dummy_password_check(cls, password: str) -> None:
        """管理者が存在しない場合も bcrypt を実行し、応答時間差を抑える。"""
        cls.verify_password(password, cls.DUMMY_PASSWORD_HASH)

    @staticmethod
    def create_access_token(
        store_manager: StoreManager,
        config: StoreManagerAuthConfig,
    ) -> str:
        """店舗管理者情報を含む HS256 JWT を発行する。"""
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(
            seconds=config.access_token_expire_seconds
        )
        payload = {
            "sub": str(store_manager.store_manager_id),
            "store_manager_id": store_manager.store_manager_id,
            "store_id": store_manager.store_id,
            "roll_id": store_manager.roll_id,
            "iat": issued_at,
            "exp": expires_at,
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, config.jwt_secret, algorithm="HS256")
