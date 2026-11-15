from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.user_controller import UserController
from app.core.exceptions.message import (
    WALLET_NOT_FOUND_ERROR,
)
from app.models.responses.wallet_permit_response import WalletPermitResponse


class TestGetUserWalletPermit:
    """get_user_wallet_permit の動作を検証する。"""

    @patch("app.controllers.user_controller.UserService")
    def test_get_user_wallet_permit(self, mock_service_class) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        user_id = 101
        expected = WalletPermitResponse(
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=11155111,
            token_symbol="JPYC",
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )
        mock_service = mock_service_class.return_value
        mock_service.get_user_wallet_permit.return_value = expected

        result = UserController.get_user_wallet_permit.__wrapped__(
            UserController(),
            mysql_session=mysql_session,
            user_id=user_id,
        )

        mock_service.get_user_wallet_permit.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        assert result == expected

    @patch("app.controllers.user_controller.UserService")
    def test_get_user_wallet_permit_returns_404_when_wallet_not_found(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        user_id = 999
        mock_service = mock_service_class.return_value
        mock_service.get_user_wallet_permit.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            UserController.get_user_wallet_permit.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                user_id=user_id,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": WALLET_NOT_FOUND_ERROR,
        }
