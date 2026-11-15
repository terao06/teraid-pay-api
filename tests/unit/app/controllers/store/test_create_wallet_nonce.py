from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    SERVER_ERROR,
    STORE_NOT_FOUND_ERROR,
)
from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
)
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse


class TestCreateWalletNonce:
    """create_wallet_nonce の動作を検証する。"""

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
