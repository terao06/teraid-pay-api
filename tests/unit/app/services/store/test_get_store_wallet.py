from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.responses.wallet_response import WalletResponse
from app.services.store_wallet_service import StoreWalletService


class TestGetStoreWallet:
    """get_store_wallet の動作を検証する。"""

    @patch("app.services.store_wallet_service.StoreWalletRepository")
    def test_get_store_wallet(self, mock_repository_class) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_info = SimpleNamespace(
            wallet_id=201,
            wallet_address="0x2222222222222222222222222222222222222222",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_permitted=False,
            verified_at=datetime(2024, 2, 10, 12, 0, 0),
            created_at=datetime(2024, 2, 1, 9, 30, 0),
            updated_at=datetime(2024, 2, 15, 18, 45, 0),
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = wallet_info

        result = StoreWalletService().get_store_wallet(mysql_session=mysql_session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        assert result == WalletResponse(
            wallet_id=201,
            wallet_address="0x2222222222222222222222222222222222222222",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_permitted=False,
            verified_at="2024-02-10 12:00",
            created_at="2024-02-01 09:30",
            updated_at="2024-02-15 18:45",
        )

    @patch("app.services.store_wallet_service.StoreWalletRepository")
    def test_get_store_wallet_returns_none_when_wallet_not_found(self, mock_repository_class) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        store_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = None

        result = StoreWalletService().get_store_wallet(mysql_session=mysql_session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        assert result is None
