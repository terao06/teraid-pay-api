from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    SERVER_ERROR,
)
from app.models.responses.wallet_response import WalletResponse


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
