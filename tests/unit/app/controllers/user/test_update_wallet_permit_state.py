from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.user_controller import UserController
from app.core.exceptions.custom_exception import (
    WalletNotPermittedException,
    WalletNotFoundException,
)
from app.core.exceptions.message import (
    SERVER_ERROR,
    WALLET_NOT_PERMITTED_ERROR,
    WALLET_NOT_FOUND_ERROR,
)


class TestUpdateWalletPermitState:
    """update_wallet_permit_state の動作を検証する。"""

    @patch("app.controllers.user_controller.UserService")
    def test_update_wallet_permit_state(self, mock_service_class) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        wallet_id = 301
        permit = {
            "value": 1000,
            "deadline": 1893456000,
            "signature_recovery_id": 27,
            "signature_first_32_bytes": "0x" + "a" * 64,
            "signature_second_32_bytes": "0x" + "b" * 64,
        }
        mock_service = mock_service_class.return_value

        result = UserController.update_wallet_permit_state.__wrapped__(
            UserController(),
            mysql_session=mysql_session,
            wallet_id=wallet_id,
            **permit,
        )

        mock_service.update_wallet_permit_state.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
            **permit,
        )
        assert result is None

    @patch("app.controllers.user_controller.UserService")
    def test_update_wallet_permit_state_raise_http_exception_when_wallet_not_found(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 999
        tx_hash = "0x" + "a" * 64
        mock_service = mock_service_class.return_value
        mock_service.update_wallet_permit_state.side_effect = WalletNotFoundException("wallet not found")

        with pytest.raises(HTTPException) as exc_info:
            UserController.update_wallet_permit_state.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                value=1000,
                deadline=1893456000,
                signature_recovery_id=27,
                signature_first_32_bytes="0x" + "a" * 64,
                signature_second_32_bytes="0x" + "b" * 64,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": WALLET_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.user_controller.UserService")
    def test_update_wallet_permit_state_raise_http_exception_when_permit_is_incomplete(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 301
        mock_service = mock_service_class.return_value
        mock_service.update_wallet_permit_state.side_effect = WalletNotPermittedException("permit is incomplete")

        with pytest.raises(HTTPException) as exc_info:
            UserController.update_wallet_permit_state.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                value=1000,
                deadline=1893456000,
                signature_recovery_id=27,
                signature_first_32_bytes="0x" + "a" * 64,
                signature_second_32_bytes="0x" + "b" * 64,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == {
            "status": "error",
            "message": WALLET_NOT_PERMITTED_ERROR,
        }

    @patch("app.controllers.user_controller.UserService")
    def test_update_wallet_permit_state_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 301
        mock_service = mock_service_class.return_value
        mock_service.update_wallet_permit_state.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            UserController.update_wallet_permit_state.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                value=1000,
                deadline=1893456000,
                signature_recovery_id=27,
                signature_first_32_bytes="0x" + "a" * 64,
                signature_second_32_bytes="0x" + "b" * 64,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
