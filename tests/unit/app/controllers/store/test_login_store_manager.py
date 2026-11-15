from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    LOGIN_FAILED_ERROR,
    STORE_MANAGER_INACTIVE_ERROR,
)
from app.core.exceptions.custom_exception import (
    StoreManagerInactiveException,
    UnauthorizedException,
)
from app.models.requests.store_manager_login_request import StoreManagerLoginRequest
from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)


class TestLoginStoreManager:
    """StoreControllerの店舗管理者ログイン処理を検証する。"""

    @patch("app.controllers.store_controller.StoreService")
    def test_login_store_manager(self, mock_service_class) -> None:
        """リクエスト値をサービスへ渡し、ログイン結果をそのまま返すことを検証する。"""
        mysql_session = Mock()
        request = StoreManagerLoginRequest(
            email="manager@example.com",
            password="password123",
        )
        expected = StoreManagerLoginResponse(
            access_token="jwt-token",
            expires_in=3600,
            store_manager=StoreManagerInfoResponse(
                store_manager_id=1,
                store_id=101,
                name="店舗管理者",
                roll_id=1,
            ),
        )
        mock_service_class.return_value.login_store_manager.return_value = expected

        result = StoreController.login_store_manager.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.login_store_manager.assert_called_once_with(
            mysql_session=mysql_session,
            email="manager@example.com",
            password="password123",
        )

    @pytest.mark.parametrize(
        ("service_error", "expected_status", "expected_message"),
        [
            (UnauthorizedException(), 401, LOGIN_FAILED_ERROR),
            (
                StoreManagerInactiveException(),
                403,
                STORE_MANAGER_INACTIVE_ERROR,
            ),
        ],
    )
    @patch("app.controllers.store_controller.StoreService")
    def test_login_converts_auth_errors(
        self,
        mock_service_class,
        service_error,
        expected_status,
        expected_message,
    ) -> None:
        """認証失敗と無効アカウントを適切なHTTPエラーへ変換することを検証する。"""
        mock_service_class.return_value.login_store_manager.side_effect = service_error
        request = StoreManagerLoginRequest(
            email="manager@example.com",
            password="password123",
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.login_store_manager.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                request=request,
            )

        assert exc_info.value.status_code == expected_status
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }
