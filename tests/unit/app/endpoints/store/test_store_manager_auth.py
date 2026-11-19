"""管理者APIで共通のBearer JWT認証を検証する。"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.aws.secret_manager import SecretManager
from app.dependencies.store_manager_auth import (
    authenticate_store_manager,
    get_store_manager_token_claims,
)


JWT_SECRET = "test-store-manager-jwt-secret-at-least-32-characters"


def create_access_token(store_id: int = 101) -> str:
    """endpoint認証テスト用の店舗管理者JWTを作成する。"""
    issued_at = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "201",
            "store_manager_id": 201,
            "store_id": store_id,
            "roll_id": 1,
            "iat": issued_at,
            "exp": issued_at + timedelta(hours=1),
            "jti": str(uuid4()),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


class TestStoreManagerJwtAuthentication:
    """store_routerに設定した店舗管理者JWT認証を検証する。"""

    @pytest.mark.parametrize(
        ("method", "path", "request_body"),
        [
            ("GET", "/store/wallet", None),
            (
                "POST",
                "/store/wallet/nonce",
                {
                    "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                    "chain_type": "ethereum",
                    "network_name": "sepolia",
                },
            ),
            (
                "POST",
                "/store/wallet",
                {
                    "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                    "signature": "signed-message",
                    "chain_type": "ethereum",
                    "network_name": "sepolia",
                    "token_symbol": "JPYC",
                    "chain_id": 11155111,
                },
            ),
            ("DELETE", "/store/wallet/301", None),
            ("POST", "/store/manager/logout", None),
        ],
    )
    def test_store_endpoints_require_bearer_token(
        self,
        client_without_store_manager_auth_override,
        method: str,
        path: str,
        request_body: dict | None,
    ) -> None:
        """ログイン以外の全store endpointがBearerトークンなしで401を返すことを検証する。"""
        response = client_without_store_manager_auth_override.request(
            method=method,
            url=path,
            json=request_body,
        )

        assert response.status_code == 401
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "認証に失敗しました。",
            }
        }
        assert response.headers["www-authenticate"] == "Bearer"

    @patch("app.endpoints.store.StoreController.get_store_wallet")
    @patch.object(SecretManager, "get_secret")
    @patch("app.dependencies.store_manager_auth.StoreManagerRepository")
    @patch("app.dependencies.store_manager_auth.get_mysql_db")
    def test_valid_token_allows_access(
        self,
        mock_get_mysql_db,
        mock_repository_class,
        mock_get_secret,
        mock_get_store_wallet,
        client_without_store_manager_auth_override,
    ) -> None:
        """署名と有効期限が正しいJWTで対象店舗へアクセスできることを検証する。"""
        mock_get_secret.return_value = {
            "store_manager_jwt_secret": JWT_SECRET,
            "store_manager_jwt_expire_seconds": 3600,
        }
        mock_repository_class.return_value.get_store_manager_by_id.return_value = (
            SimpleNamespace(
                store_manager_id=201,
                store_id=101,
                name="Store Manager 1",
                email="manager1@example.com",
                roll_id=1,
                is_active=True,
            )
        )
        mock_get_store_wallet.return_value = None
        mock_repository_class.return_value.is_access_token_revoked.return_value = False

        response = client_without_store_manager_auth_override.get(
            "/store/wallet",
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": None}
        mock_get_store_wallet.assert_called_once_with(store_id=101)
        mock_repository_class.return_value.get_store_manager_by_id.assert_called_once_with(
            mysql_session=(
                mock_get_mysql_db.return_value.get_session.return_value
                .__enter__.return_value
            ),
            store_manager_id=201,
        )

    @patch.object(SecretManager, "get_secret")
    @patch("app.dependencies.store_manager_auth.StoreManagerRepository")
    @patch("app.dependencies.store_manager_auth.get_mysql_db")
    def test_authenticate_store_manager_returns_user_information(
        self,
        mock_get_mysql_db,
        mock_repository_class,
        mock_get_secret,
    ) -> None:
        """認証成功時にDB上の店舗管理者ユーザー情報を返すことを検証する。"""
        mock_get_secret.return_value = {
            "store_manager_jwt_secret": JWT_SECRET,
            "store_manager_jwt_expire_seconds": 3600,
        }
        mock_repository_class.return_value.get_store_manager_by_id.return_value = (
            SimpleNamespace(
                store_manager_id=201,
                store_id=101,
                name="Store Manager 1",
                email="manager1@example.com",
                roll_id=1,
                is_active=True,
            )
        )

        mock_repository_class.return_value.is_access_token_revoked.return_value = False
        claims = get_store_manager_token_claims(
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=create_access_token(),
            ),
        )
        result = authenticate_store_manager(claims)

        assert result.store_manager_id == 201
        assert result.store_id == 101
        assert result.name == "Store Manager 1"
        assert result.email == "manager1@example.com"
        assert result.roll_id == 1
        assert result.is_active is True
