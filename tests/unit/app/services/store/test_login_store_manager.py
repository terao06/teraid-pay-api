from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    StoreManagerInactiveException,
    UnauthorizedException,
)
from app.core.config.store_manager_auth import StoreManagerAuthConfig
from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)
from app.services.store_auth_service import StoreAuthService


class TestLoginStoreManager:
    """StoreAuthServiceの店舗管理者ログイン処理を検証する。"""

    @patch("app.services.store_auth_service.get_store_manager_auth_config")
    @patch("app.services.store_auth_service.StoreManagerAuthUtil")
    @patch("app.services.store_auth_service.StoreManagerRepository")
    def test_login_store_manager(
        self,
        mock_repository_class,
        mock_auth_util,
        mock_get_auth_config,
    ) -> None:
        """認証成功時にメールアドレスを正規化し、JWTと管理者情報を返すことを検証する。"""
        mysql_session = Mock()
        store_manager = SimpleNamespace(
            store_manager_id=1,
            store_id=101,
            name="店舗管理者",
            email="manager@example.com",
            password_hash="bcrypt-hash",
            roll_id=2,
            is_active=True,
        )
        mock_repository_class.return_value.get_store_manager_by_email.return_value = (
            store_manager
        )
        mock_auth_util.verify_password.return_value = True
        mock_auth_util.create_access_token.return_value = "jwt-token"
        config = StoreManagerAuthConfig(
            jwt_secret="x" * 32,
            access_token_expire_seconds=3600,
        )
        mock_get_auth_config.return_value = config

        result = StoreAuthService().login_store_manager(
            mysql_session=mysql_session,
            email=" Manager@Example.com ",
            password="password123",
        )

        assert result == StoreManagerLoginResponse(
            access_token="jwt-token",
            expires_in=3600,
            store_manager=StoreManagerInfoResponse(
                store_manager_id=1,
                store_id=101,
                name="店舗管理者",
                roll_id=2,
            ),
        )
        mock_repository_class.return_value.get_store_manager_by_email.assert_called_once_with(
            mysql_session=mysql_session,
            email="manager@example.com",
        )
        mock_auth_util.verify_password.assert_called_once_with(
            password="password123",
            password_hash="bcrypt-hash",
        )
        mock_auth_util.create_access_token.assert_called_once_with(
            store_manager=store_manager,
            config=config,
        )

    @patch("app.services.store_auth_service.StoreManagerAuthUtil")
    @patch("app.services.store_auth_service.StoreManagerRepository")
    def test_login_rejects_unknown_email(
        self,
        mock_repository_class,
        mock_auth_util,
    ) -> None:
        """管理者が存在しない場合にダミー照合を実行して認証エラーにすることを検証する。"""
        mock_repository_class.return_value.get_store_manager_by_email.return_value = None

        with pytest.raises(UnauthorizedException):
            StoreAuthService().login_store_manager(
                mysql_session=Mock(),
                email="missing@example.com",
                password="password123",
            )

        mock_auth_util.perform_dummy_password_check.assert_called_once_with(
            "password123"
        )

    @patch("app.services.store_auth_service.StoreManagerAuthUtil")
    @patch("app.services.store_auth_service.StoreManagerRepository")
    def test_login_rejects_inactive_manager(
        self,
        mock_repository_class,
        mock_auth_util,
    ) -> None:
        """パスワードが一致しても無効な管理者はログインできないことを検証する。"""
        store_manager = SimpleNamespace(
            password_hash="bcrypt-hash",
            is_active=False,
        )
        mock_repository_class.return_value.get_store_manager_by_email.return_value = (
            store_manager
        )
        mock_auth_util.verify_password.return_value = True

        with pytest.raises(StoreManagerInactiveException):
            StoreAuthService().login_store_manager(
                mysql_session=Mock(),
                email="inactive@example.com",
                password="password123",
            )
