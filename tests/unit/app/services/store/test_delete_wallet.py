from unittest.mock import Mock, patch

import pytest

from app.services.store_wallet_service import StoreWalletService


class TestDeleteWallet:
    """StoreWalletService の delete_wallet を検証するテスト。"""

    @patch("app.services.store_wallet_service.StoreWalletRepository")
    @patch("app.services.store_wallet_service.WalletRepository")
    def test_delete_wallet(self, mock_wallet_repository_class, mock_store_repository_class):
        """WalletRepositoryとStoreWalletRepositoryの削除処理が正しい引数で呼ばれることを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_id = 42

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet_link.return_value = Mock()

        StoreWalletService().delete_wallet(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )

        mock_store_repository.get_store_wallet_link.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )
        mock_wallet_repository.delete_wallet_by_wallet_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_store_repository.delete_store_wallet_by_wallet_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )

    @patch("app.services.store_wallet_service.StoreWalletRepository")
    @patch("app.services.store_wallet_service.WalletRepository")
    def test_delete_wallet_store_repository_not_called_when_wallet_repository_raises(
        self,
        mock_wallet_repository_class,
        mock_store_repository_class,
    ):
        """WalletRepositoryが例外を送出した場合、StoreWalletRepositoryの削除処理を呼ばないことを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_id = 42

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet_link.return_value = Mock()
        mock_wallet_repository.delete_wallet_by_wallet_id.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            StoreWalletService().delete_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_id=wallet_id,
            )

        mock_wallet_repository.delete_wallet_by_wallet_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_store_repository.delete_store_wallet_by_wallet_id.assert_not_called()
