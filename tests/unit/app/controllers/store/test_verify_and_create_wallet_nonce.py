from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    STORE_NOT_FOUND_ERROR,
    VERIFY_ERROR,
    WALLET_CONFLICT_ERROR,
)
from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
    UnauthorizedException,
    WalletConflictException,
)
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse


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
