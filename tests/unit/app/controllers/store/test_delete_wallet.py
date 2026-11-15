from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    SERVER_ERROR,
)


class TestDeleteWallet:
    """delete_wallet の単体テスト。"""

    @patch("app.controllers.store_controller.StoreWalletService")
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

    @patch("app.controllers.store_controller.StoreWalletService")
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
