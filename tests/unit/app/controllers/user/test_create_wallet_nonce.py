from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.user_controller import UserController
from app.core.exceptions.custom_exception import (
    UserNotFoundException,
    WalletConflictException,
)
from app.core.exceptions.message import (
    SERVER_ERROR,
    USER_NOT_FOUND_ERROR,
    WALLET_IS_ALREADY_EXIST,
)
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse


class TestCreateWalletNonce:
    """create_wallet_nonce の動作を検証する。"""

    @patch("app.controllers.user_controller.UserService")
    def test_create_wallet_nonce(self, mock_service_class) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        user_id = 10
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.return_value = WalletNonceCreateResponse(
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

        result = UserController.create_wallet_nonce.__wrapped__(
            UserController(),
            mysql_session=mysql_session,
            user_id=user_id,
            request=request,
        )

        mock_service.create_wallet_nonce.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
            wallet_address=request.wallet_address,
            chain_type=request.chain_type,
            network_name=request.network_name,
        )
        assert result == WalletNonceCreateResponse(
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

    @patch("app.controllers.user_controller.UserService")
    def test_create_wallet_nonce_raise_http_exception_when_user_not_found(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        user_id = 999
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.side_effect = UserNotFoundException("user not found")

        with pytest.raises(HTTPException) as exc_info:
            UserController.create_wallet_nonce.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                user_id=user_id,
                request=request,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": USER_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.user_controller.UserService")
    def test_create_wallet_nonce_raise_http_exception_when_wallet_conflict(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        user_id = 10
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.side_effect = WalletConflictException("wallet conflict")

        with pytest.raises(HTTPException) as exc_info:
            UserController.create_wallet_nonce.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                user_id=user_id,
                request=request,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": WALLET_IS_ALREADY_EXIST,
        }

    @patch("app.controllers.user_controller.UserService")
    def test_create_wallet_nonce_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        user_id = 10
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            UserController.create_wallet_nonce.__wrapped__(
                UserController(),
                mysql_session=mysql_session,
                user_id=user_id,
                request=request,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
