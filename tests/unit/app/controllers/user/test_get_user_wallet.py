from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.user_controller import UserController
from app.core.exceptions.message import (
    SERVER_ERROR,
)
from app.models.responses.wallet_response import WalletResponse


class TestGetUserWallet:
    """get_user_wallet の単体テスト。"""

    @patch("app.controllers.user_controller.UserService")
    def test_get_user_wallet(self, mock_service_class) -> None:
        """service の戻り値をそのまま返すことを確認する。"""
        mysql_session = Mock()
        user_id = 101
        expected = WalletResponse(
            wallet_id=301,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_permitted=False,
            verified_at="2024-01-10 12:00",
            created_at="2024-01-01 09:30",
            updated_at="2024-01-15 18:45",
        )
        mock_service = mock_service_class.return_value
        mock_service.get_user_wallet.return_value = expected

        result = UserController.get_user_wallet.__wrapped__(
            UserController(),
            mysql_session=mysql_session,
            user_id=user_id,
        )

        mock_service.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        assert result == expected

    @patch("app.controllers.user_controller.UserService")
    def test_get_user_wallet_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """service で例外が発生した場合に HTTPException へ変換されることを確認する。"""
        mysql_session = Mock()
        user_id = 101
        mock_service = mock_service_class.return_value
        mock_service.get_user_wallet.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            UserController.get_user_wallet.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                user_id=user_id,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
