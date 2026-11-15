from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
    WalletConflictException,
)
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.core.utils.datetime import JST
from app.services.store_wallet_service import StoreWalletService


class TestCreateWalletNonce:
    """StoreWalletService の create_wallet_nonce を検証するテスト。"""

    @patch("app.services.store_wallet_service.secrets.token_urlsafe", return_value="generated-nonce")
    @patch("app.services.store_wallet_service.StoreWalletRepository")
    @patch("app.services.store_wallet_service.StoreManagerRepository")
    @patch("app.services.store_wallet_service.NonceRepository")
    @patch("app.services.store_wallet_service.WalletRepository")
    def test_create_wallet_nonce(
        self,
        mock_wallet_repository_class,
        mock_nonce_repository_class,
        mock_store_manager_repository_class,
        mock_store_repository_class,
        mock_token_urlsafe,
    ):
        """nonce を生成して保存し、レスポンスへ整形することを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        mock_store_manager_repository = mock_store_manager_repository_class.return_value
        mock_store_manager_repository.get_store_by_id.return_value = SimpleNamespace(store_id=store_id)
        mock_store_repository = mock_store_repository_class.return_value

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.get_wallet_by_address.return_value = None

        mock_nonce_repository = mock_nonce_repository_class.return_value
        mock_nonce_repository.create_nonce.side_effect = (
            lambda mysql_session, nonce: SimpleNamespace(nonce_id=123, nonce=nonce.nonce)
        )

        with patch("app.services.store_wallet_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreWalletService().create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_store_manager_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_wallet_repository.get_wallet_by_address.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_address=wallet_address,
        )
        mock_token_urlsafe.assert_called_once_with(32)
        mock_nonce_repository.create_nonce.assert_called_once()
        mock_store_repository.create_store_nonce.assert_called_once()

        nonce_kwargs = mock_nonce_repository.create_nonce.call_args.kwargs
        assert nonce_kwargs["mysql_session"] is mysql_session
        created_nonce = nonce_kwargs["nonce"]
        assert created_nonce.wallet_address == wallet_address.lower()
        assert created_nonce.chain_type == chain_type
        assert created_nonce.network_name == network_name
        assert created_nonce.nonce == "generated-nonce"
        assert created_nonce.expires_at == fixed_now + timedelta(minutes=10)

        store_nonce_kwargs = mock_store_repository.create_store_nonce.call_args.kwargs
        assert store_nonce_kwargs["mysql_session"] is mysql_session
        created_store_nonce = store_nonce_kwargs["store_nonce"]
        assert created_store_nonce.store_id == store_id
        assert created_store_nonce.nonce_id == 123
        assert result == WalletNonceCreateResponse(
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

    @patch("app.services.store_wallet_service.WalletRepository")
    @patch("app.services.store_wallet_service.StoreWalletRepository")
    @patch("app.services.store_wallet_service.StoreManagerRepository")
    def test_create_wallet_nonce_not_found_error(
        self,
        mock_store_manager_repository_class,
        mock_repository_class,
        mock_wallet_repository_class,
    ):
        """店舗が存在しない場合に StoreNotFoundException を送出することを検証する。"""
        mysql_session = Mock()
        store_id = 999
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_store_manager_repository = mock_store_manager_repository_class.return_value
        mock_store_manager_repository.get_store_by_id.return_value = None
        mock_repository = mock_repository_class.return_value

        with pytest.raises(StoreNotFoundException):
            StoreWalletService().create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_store_manager_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_wallet_repository_class.return_value.get_wallet_by_address.assert_not_called()
        mock_repository.create_nonce.assert_not_called()
        mock_repository.create_store_nonce.assert_not_called()

    @patch("app.services.store_wallet_service.secrets.token_urlsafe")
    @patch("app.services.store_wallet_service.StoreWalletRepository")
    @patch("app.services.store_wallet_service.StoreManagerRepository")
    @patch("app.services.store_wallet_service.NonceRepository")
    @patch("app.services.store_wallet_service.WalletRepository")
    def test_create_wallet_nonce_wallet_conflict_error(
        self,
        mock_wallet_repository_class,
        mock_nonce_repository_class,
        mock_store_manager_repository_class,
        mock_store_repository_class,
        mock_token_urlsafe,
    ):
        """ウォレットが既に存在する場合に WalletConflictException を送出することを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_store_manager_repository = mock_store_manager_repository_class.return_value
        mock_store_manager_repository.get_store_by_id.return_value = SimpleNamespace(store_id=store_id)
        mock_store_repository = mock_store_repository_class.return_value

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.get_wallet_by_address.return_value = SimpleNamespace(wallet_id=1)

        with pytest.raises(WalletConflictException):
            StoreWalletService().create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_store_manager_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_wallet_repository.get_wallet_by_address.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_address=wallet_address,
        )
        mock_token_urlsafe.assert_not_called()
        mock_nonce_repository_class.return_value.create_nonce.assert_not_called()
        mock_store_repository.create_store_nonce.assert_not_called()
