from unittest.mock import patch

import jwt
import pytest

from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)


class TestLoginStoreManagerEndpoint:
    """店舗管理者ログインAPIのエンドポイントを検証する。"""

    @patch("app.endpoints.store.StoreController.login_store_manager")
    def test_login_returns_wrapped_success(
        self,
        mock_login_store_manager,
        client,
    ) -> None:
        """ログイン成功時に共通レスポンス形式で認証情報を返すことを検証する。"""
        mock_login_store_manager.return_value = StoreManagerLoginResponse(
            access_token="jwt-token",
            expires_in=3600,
            store_manager=StoreManagerInfoResponse(
                store_manager_id=1,
                store_id=101,
                name="店舗管理者",
                roll_id=1,
            ),
        )

        response = client.post(
            "/store/manager/login",
            json={
                "email": "manager@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "access_token": "jwt-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "store_manager": {
                    "store_manager_id": 1,
                    "store_id": 101,
                    "name": "店舗管理者",
                    "roll_id": 1,
                },
            },
        }
        request = mock_login_store_manager.call_args.kwargs["request"]
        assert request.email == "manager@example.com"
        assert request.password == "password123"

    @patch("app.endpoints.store.StoreController.login_store_manager")
    def test_login_rejects_short_password(
        self,
        mock_login_store_manager,
        client,
    ) -> None:
        """短すぎるパスワードを422として拒否し、コントローラーを呼ばないことを検証する。"""
        response = client.post(
            "/store/manager/login",
            json={
                "email": "manager@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422
        mock_login_store_manager.assert_not_called()

    @pytest.mark.usefixtures("insert_store_managers")
    def test_with_db(self, client_with_db) -> None:
        """DB上の管理者を認証し、有効なJWTと管理者情報を返すことを検証する。"""
        response = client_with_db.post(
            "/store/manager/login",
            json={
                "email": "manager1@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        response_data = response.json()["data"]
        assert response.json()["status"] == "success"
        assert response_data["token_type"] == "Bearer"
        assert response_data["expires_in"] == 3600
        assert response_data["store_manager"] == {
            "store_manager_id": 201,
            "store_id": 101,
            "name": "Store Manager 1",
            "roll_id": 1,
        }

        payload = jwt.decode(
            response_data["access_token"],
            "test-store-manager-jwt-secret-at-least-32-characters",
            algorithms=["HS256"],
        )
        assert payload["sub"] == "201"
        assert payload["store_manager_id"] == 201
        assert payload["store_id"] == 101
        assert payload["roll_id"] == 1
