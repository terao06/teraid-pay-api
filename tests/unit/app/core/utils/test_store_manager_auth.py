from types import SimpleNamespace

import bcrypt
import jwt

from app.core.config.store_manager_auth import StoreManagerAuthConfig
from app.core.utils.store_manager_auth import StoreManagerAuthUtil


class TestStoreManagerAuthUtil:
    """店舗管理者認証ユーティリティを検証する。"""

    def test_verify_password(self) -> None:
        """正しいパスワードのみbcryptハッシュとの照合に成功することを検証する。"""
        password_hash = bcrypt.hashpw(
            b"password123",
            bcrypt.gensalt(rounds=4),
        ).decode("utf-8")

        assert StoreManagerAuthUtil.verify_password(
            "password123",
            password_hash,
        )
        assert not StoreManagerAuthUtil.verify_password(
            "wrong-password",
            password_hash,
        )

    def test_create_access_token(self) -> None:
        """JWTに管理者識別情報、有効期限、一意なIDが設定されることを検証する。"""
        config = StoreManagerAuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-characters",
            access_token_expire_seconds=3600,
        )
        store_manager = SimpleNamespace(
            store_manager_id=1,
            store_id=101,
            roll_id=2,
        )

        token = StoreManagerAuthUtil.create_access_token(
            store_manager=store_manager,
            config=config,
        )
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=["HS256"],
        )

        assert payload["sub"] == "1"
        assert payload["store_manager_id"] == 1
        assert payload["store_id"] == 101
        assert payload["roll_id"] == 2
        assert payload["exp"] - payload["iat"] == 3600
        assert payload["jti"]
