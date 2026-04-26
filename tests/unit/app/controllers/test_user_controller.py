from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.user_controller import UserController
from app.core.exceptions.custom_exception import UnauthorizedException, UserNotFoundException, WalletConflictException
from app.core.exceptions.message import SERVER_ERROR, USER_NOT_FOUND_ERROR, VERIFY_ERROR, WALLET_CONFLICT_ERROR
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.models.responses.wallet_response import WalletResponse


class TestGetUserWallet:
    """get_user_wallet の unit test。"""

    @patch("app.controllers.user_controller.UserService")
    def test_get_user_wallet(self, mock_service_class) -> None:
        """service の戻り値をそのまま返すことを確認する。"""
        session = Mock()
        user_id = 101
        expected = WalletResponse(
            wallet_id=301,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_type="ETH",
            network_name="mainnet",
            chain_id=1,
            is_active=True,
            verified_at="2024-01-10 12:00",
            created_at="2024-01-01 09:30",
            updated_at="2024-01-15 18:45",
        )
        mock_service = mock_service_class.return_value
        mock_service.get_user_wallet.return_value = expected

        result = UserController.get_user_wallet.__wrapped__(
            UserController(),
            session=session,
            user_id=user_id,
        )

        mock_service.get_user_wallet.assert_called_once_with(
            session=session,
            user_id=user_id,
        )
        assert result == expected

    @patch("app.controllers.user_controller.UserService")
    def test_get_user_wallet_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """service で例外が発生した場合に HTTPException へ変換されることを確認する。"""
        session = Mock()
        user_id = 101
        mock_service = mock_service_class.return_value
        mock_service.get_user_wallet.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            UserController.get_user_wallet.__wrapped__(
                UserController(),
                session=session,
                user_id=user_id,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }


class TestCreateWalletNonce:
    @patch("app.controllers.user_controller.UserService")
    def test_create_wallet_nonce(self, mock_service_class) -> None:
        session = Mock()
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
            session=session,
            user_id=user_id,
            request=request,
        )

        mock_service.create_wallet_nonce.assert_called_once_with(
            session=session,
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
        session = Mock()
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
                session=session,
                user_id=user_id,
                request=request,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": USER_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.user_controller.UserService")
    def test_create_wallet_nonce_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        session = Mock()
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
                session=session,
                user_id=user_id,
                request=request,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }


class TestVerifyAndCreateWalletNonce:
    @patch("app.controllers.user_controller.UserService")
    def test_verify_and_create_wallet_nonce(self, mock_service_class) -> None:
        session = Mock()
        user_id = 10
        request = WalletVerifyRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            signature="signed-message",
            chain_type="ethereum",
            network_name="sepolia",
            chain_id=11155111,
        )
        nonce_entity = Mock()
        expected = WalletVerifyResponse(
            wallet_address=request.wallet_address,
            chain_type=request.chain_type,
            network_name=request.network_name,
            chain_id=request.chain_id,
            is_active=True,
            verified_at="2026-04-12 12:10",
        )
        mock_service = mock_service_class.return_value
        mock_service.verify_wallet_nonce.return_value = nonce_entity
        mock_service.create_store_wallet.return_value = expected

        result = UserController.verify_and_create_wallet_nonce.__wrapped__(
            UserController(),
            session=session,
            user_id=user_id,
            request=request,
        )

        mock_service.verify_wallet_nonce.assert_called_once_with(
            session=session,
            user_id=user_id,
            wallet_address=request.wallet_address,
            signature=request.signature,
            chain_type=request.chain_type,
            network_name=request.network_name,
        )
        mock_service.create_store_wallet.assert_called_once_with(
            session=session,
            user_id=user_id,
            wallet_address=request.wallet_address,
            chain_type=request.chain_type,
            network_name=request.network_name,
            chain_id=request.chain_id,
            nonce_entity=nonce_entity,
        )
        assert result == expected

    @patch("app.controllers.user_controller.UserService")
    @pytest.mark.parametrize(
        ("verify_side_effect", "create_side_effect", "expected_status_code", "expected_message"),
        [
            (UserNotFoundException("user not found"), None, 404, USER_NOT_FOUND_ERROR),
            (UnauthorizedException("verify failed"), None, 401, VERIFY_ERROR),
            (None, WalletConflictException("wallet conflict"), 409, WALLET_CONFLICT_ERROR),
        ],
    )
    def test_verify_and_create_wallet_nonce_raise_http_exception(
        self,
        mock_service_class,
        verify_side_effect,
        create_side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        session = Mock()
        user_id = 10
        request = WalletVerifyRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            signature="signed-message",
            chain_type="ethereum",
            network_name="sepolia",
            chain_id=11155111,
        )
        nonce_entity = Mock()
        mock_service = mock_service_class.return_value
        mock_service.verify_wallet_nonce.return_value = nonce_entity
        mock_service.verify_wallet_nonce.side_effect = verify_side_effect
        mock_service.create_store_wallet.side_effect = create_side_effect

        with pytest.raises(HTTPException) as exc_info:
            UserController.verify_and_create_wallet_nonce.__wrapped__(
                UserController(),
                session=session,
                user_id=user_id,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }


class TestDeleteWallet:
    @patch("app.controllers.user_controller.UserService")
    def test_delete_wallet(self, mock_service_class) -> None:
        session = Mock()
        wallet_id = 42
        mock_service = mock_service_class.return_value

        result = UserController.delete_wallet.__wrapped__(
            UserController(),
            session=session,
            wallet_id=wallet_id,
        )

        mock_service.delete_wallet.assert_called_once_with(
            session=session,
            wallet_id=wallet_id,
        )
        assert result is None

    @patch("app.controllers.user_controller.UserService")
    def test_delete_wallet_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        session = Mock()
        wallet_id = 42
        mock_service = mock_service_class.return_value
        mock_service.delete_wallet.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            UserController.delete_wallet.__wrapped__(
                UserController(),
                session=session,
                wallet_id=wallet_id,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
