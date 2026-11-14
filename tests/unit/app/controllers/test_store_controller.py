from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    LOGIN_FAILED_ERROR,
    SERVER_ERROR,
    STORE_MANAGER_INACTIVE_ERROR,
    STORE_NOT_FOUND_ERROR,
    VERIFY_ERROR,
    WALLET_CONFLICT_ERROR,
)
from app.core.exceptions.custom_exception import (
    StoreManagerInactiveException,
    StoreNotFoundException,
    UnauthorizedException,
    WalletConflictException,
)
from app.models.requests.store_manager_login_request import StoreManagerLoginRequest
from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.responses.wallet_response import WalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse


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


class TestGetStoreWallet:
    """StoreController の単体テスト。"""

    @patch("app.controllers.store_controller.StoreService")
    def test_get_store_wallet(self, mock_service_class) -> None:
        """サービスの戻り値をそのまま返し、引数を正しく引き渡すことを確認する。"""

        mysql_session = Mock()
        store_id = 10
        expected = WalletResponse(
            wallet_id=1,
            wallet_address="wallet-address-1",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_permitted=False,
            verified_at="2026-04-12 12:00",
            created_at="2026-04-12 12:00",
            updated_at="2026-04-12 12:00",
        )
        mock_service = mock_service_class.return_value
        mock_service.get_store_wallet.return_value = expected

        result = StoreController.get_store_wallet.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=store_id,
        )

        mock_service.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        assert result == expected

    @patch("app.controllers.store_controller.StoreService")
    def test_get_store_wallet_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """想定外例外がサーバーエラーの HTTPException に変換されることを確認する。"""

        mysql_session = Mock()
        store_id = 10
        mock_service = mock_service_class.return_value
        mock_service.get_store_wallet.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_store_wallet.__wrapped__(
                StoreController(),
                mysql_session=mysql_session,
                store_id=store_id,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }

class TestCreateWalletNonce:
    @patch("app.controllers.store_controller.StoreService")
    def test_create_wallet_nonce(self, mock_service_class) -> None:
        """nonce 作成処理がサービスに正しく委譲されることを確認する。"""

        mysql_session = Mock()
        store_id = 10
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.return_value = WalletNonceCreateResponse(
            message="sign this message",
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

        result = StoreController.create_wallet_nonce.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=store_id,
            request=request,
        )

        mock_service.create_wallet_nonce.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_address=request.wallet_address,
            chain_type=request.chain_type,
            network_name=request.network_name,
        )
        assert result == WalletNonceCreateResponse(
            message="sign this message",
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

    @patch("app.controllers.store_controller.StoreService")
    def test_create_wallet_nonce_raise_http_exception_when_store_not_found(
        self,
        mock_service_class,
    ) -> None:
        """店舗が見つからない場合に 404 の HTTPException へ変換されることを確認する。"""

        mysql_session = Mock()
        store_id = 999
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.side_effect = StoreNotFoundException("store not found")

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_wallet_nonce.__wrapped__(
                StoreController(),
                mysql_session=mysql_session,
                store_id=store_id,
                request=request,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": STORE_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.store_controller.StoreService")
    def test_create_wallet_nonce_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """予期しない例外が発生した場合に 500 の HTTPException へ変換されることを確認する。"""

        mysql_session = Mock()
        store_id = 10
        request = WalletNonceCreateRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            chain_type="ethereum",
            network_name="sepolia",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_wallet_nonce.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_wallet_nonce.__wrapped__(
                StoreController(),
                mysql_session=mysql_session,
                store_id=store_id,
                request=request,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }


class TestVerifyAndCreateWalletNonce:
    """verify_and_create_wallet_nonce の単体テスト。"""

    @patch("app.controllers.store_controller.StoreService")
    def test_verify_and_create_wallet_nonce(self, mock_service_class) -> None:
        """nonce 検証成功後にウォレット作成結果を返すことを確認する。"""

        mysql_session = Mock()
        store_id = 10
        request = WalletVerifyRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            signature="signed-message",
            chain_type="ethereum",
            network_name="sepolia",
            token_symbol="JPYC",
            chain_id=11155111,
        )
        nonce_entity = Mock()
        expected = WalletVerifyResponse(
            wallet_address=request.wallet_address,
            chain_type=request.chain_type,
            network_name=request.network_name,
            token_symbol=request.token_symbol,
            chain_id=request.chain_id,
            is_active=True,
            is_permitted=True,
            verified_at="2026-04-12 12:10",
        )
        mock_service = mock_service_class.return_value
        mock_service.verify_wallet_nonce.return_value = nonce_entity
        mock_service.create_store_wallet.return_value = expected

        result = StoreController.verify_and_create_wallet_nonce.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=store_id,
            request=request,
        )

        mock_service.verify_wallet_nonce.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_address=request.wallet_address,
            signature=request.signature,
            chain_type=request.chain_type,
            network_name=request.network_name,
        )
        mock_service.create_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_address=request.wallet_address,
            chain_type=request.chain_type,
            network_name=request.network_name,
            token_symbol=request.token_symbol,
            chain_id=request.chain_id,
            nonce_entity=nonce_entity,
        )
        assert result == expected

    @patch("app.controllers.store_controller.StoreService")
    @pytest.mark.parametrize(
        ("verify_side_effect", "create_side_effect", "expected_status_code", "expected_message"),
        [
            (StoreNotFoundException("store not found"), None, 404, STORE_NOT_FOUND_ERROR),
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
        """各例外が期待する HTTPException に変換されることを確認する。"""

        mysql_session = Mock()
        store_id = 10
        request = WalletVerifyRequest(
            wallet_address="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            signature="signed-message",
            chain_type="ethereum",
            network_name="sepolia",
            token_symbol="JPYC",
            chain_id=11155111,
        )
        nonce_entity = Mock()
        mock_service = mock_service_class.return_value
        mock_service.verify_wallet_nonce.return_value = nonce_entity
        mock_service.verify_wallet_nonce.side_effect = verify_side_effect
        mock_service.create_store_wallet.side_effect = create_side_effect

        with pytest.raises(HTTPException) as exc_info:
            StoreController.verify_and_create_wallet_nonce.__wrapped__(
                StoreController(),
                mysql_session=mysql_session,
                store_id=store_id,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }


class TestDeleteWallet:
    """delete_wallet の単体テスト。"""

    @patch("app.controllers.store_controller.StoreService")
    def test_delete_wallet(self, mock_service_class) -> None:
        """削除処理がサービスへ正しく委譲されることを確認する。"""

        mysql_session = Mock()
        store_id = 10
        wallet_id = 42
        mock_service = mock_service_class.return_value

        result = StoreController.delete_wallet.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )

        mock_service.delete_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )
        assert result is None

    @patch("app.controllers.store_controller.StoreService")
    def test_delete_wallet_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """想定外例外がサーバーエラーの HTTPException に変換されることを確認する。"""

        mysql_session = Mock()
        store_id = 10
        wallet_id = 42
        mock_service = mock_service_class.return_value
        mock_service.delete_wallet.side_effect = Exception("unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            StoreController.delete_wallet.__wrapped__(
                StoreController(),
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_id=wallet_id,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
