"""店舗管理者ログアウトと失効後の認証を検証する。"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from sqlalchemy.orm import Session

from app.core.config.store_manager_auth import get_store_manager_auth_config
from app.models.mysql.store_manager_revoked_token import StoreManagerRevokedToken


class TestLogoutStoreManagerEndpoint:
    """ログアウトAPIと既存の店舗管理者APIの動作を検証する。

    Args:
        なし。

    Returns:
        pytestが実行するテストのインスタンス。
    """

    @pytest.mark.parametrize("is_expired", [False, True])
    def test_rejects_invalid_bearer_token(
        self, client_without_store_manager_auth_override, is_expired: bool
    ) -> None:
        """不正なJWTと期限切れJWTは、DBにアクセスせず401を返す。

        Args:
            client_without_store_manager_auth_override: 実際の認証処理を使うクライアント。
            is_expired: 期限切れJWTを使用する場合はTrue。

        Returns:
            なし。
        """
        secret = "unit-test-store-manager-key-32-chars"
        token = "invalid-token"
        if is_expired:
            issued_at = datetime.now(timezone.utc) - timedelta(hours=2)
            token = jwt.encode(
                {
                    "sub": "201",
                    "store_manager_id": 201,
                    "roll_id": 1,
                    "iat": issued_at,
                    "exp": issued_at + timedelta(hours=1),
                    "jti": "expired-test-jti",
                },
                secret,
                algorithm="HS256",
            )
        with (
            patch("app.dependencies.store_manager_auth.get_store_manager_auth_config") as config,
            patch("app.dependencies.store_manager_auth.get_mysql_db") as get_db,
        ):
            config.return_value.jwt_secret = secret
            response = client_without_store_manager_auth_override.post(
                "/store/manager/logout", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        get_db.assert_not_called()

    def test_with_db_revokes_only_the_presented_token(
        self, store_client_with_db, mysql_session: Session
    ) -> None:
        """失効を確定し、同じJWTの再利用だけを拒否する。

        Args:
            store_client_with_db: ログイン済みJWTを持ち、実際のMySQLに接続するAPIクライアント。
            mysql_session: コミット済みの失効レコードを確認するセッション。

        Returns:
            なし。
        """
        existing_token = store_client_with_db.headers["Authorization"].removeprefix("Bearer ")
        secret = get_store_manager_auth_config().jwt_secret
        payload = jwt.decode(existing_token, secret, algorithms=["HS256"])
        jti = "8bae2a58-0607-4d40-9d8e-d88df08a49d2"
        token = jwt.encode({**payload, "jti": jti}, secret, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        assert store_client_with_db.get("/store/wallet", headers=headers).status_code == 200

        logout = store_client_with_db.post("/store/manager/logout", headers=headers)

        assert logout.status_code == 204
        assert logout.content == b""
        revoked = mysql_session.get(StoreManagerRevokedToken, jti)
        assert revoked is not None
        assert revoked.store_manager_id == payload["store_manager_id"]
        expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc).replace(tzinfo=None)
        assert revoked.expires_at == expires_at
        assert revoked.created_at < revoked.expires_at

        for attempt in (
            store_client_with_db.get("/store/wallet", headers=headers),
            store_client_with_db.post("/store/manager/logout", headers=headers),
        ):
            assert attempt.status_code == 401
            assert attempt.headers["www-authenticate"] == "Bearer"
        assert store_client_with_db.get("/store/wallet").status_code == 200
