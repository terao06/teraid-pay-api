from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.user_controller import UserController
from app.core.exceptions.message import (
    SERVER_ERROR,
)


class TestDeleteWallet:
    """delete_wallet の動作を検証する。"""

    @patch("app.controllers.user_controller.UserService")
    def test_delete_wallet(self, mock_service_class) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        wallet_id = 42
        mock_service = mock_service_class.return_value

        result = UserController.delete_wallet.__wrapped__(
            UserController(),
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )

        mock_service.delete_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        assert result is None

    @patch("app.controllers.user_controller.UserService")
    def test_delete_wallet_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 42
        mock_service = mock_service_class.return_value
        mock_service.delete_wallet.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            UserController.delete_wallet.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                wallet_id=wallet_id,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
