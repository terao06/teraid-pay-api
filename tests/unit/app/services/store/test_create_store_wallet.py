from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    WalletConflictException,
)
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.services.store_service import StoreService


class TestCreateStoreWallet:
    """StoreService の create_store_wallet を検証するテスト。"""

    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.WalletRepository")
    @patch("app.services.store_service.NonceRepository")
    def test_create_store_wallet(self, mock_nonce_repository_class, mock_wallet_repository_class, mock_store_repository_class):
        """primary の切り替えと nonce の使用済み更新を行い、レスポンスを返すことを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        normalized_wallet_address = wallet_address.lower()
        chain_type = "ethereum"
        network_name = "sepolia"
        token_symbol = "JPYC"
        chain_id = 11155111
        fixed_now = datetime(2026, 4, 12, 12, 34, 56)
        nonce_entity = SimpleNamespace(nonce_id=1, used_at=None)

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_wallet_by_store_id.return_value = None
        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.create_wallet.return_value = SimpleNamespace(wallet_id=77)

        mock_nonce_repository = mock_nonce_repository_class.return_value


        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreService().create_store_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                token_symbol=token_symbol,
                chain_id=chain_id,
                nonce_entity=nonce_entity,
            )

        mock_store_repository.get_wallet_by_store_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )

        mock_wallet_repository.create_wallet.assert_called_once()
        create_wallet_kwargs = mock_wallet_repository.create_wallet.call_args.kwargs
        assert create_wallet_kwargs["mysql_session"] is mysql_session
        created_wallet = create_wallet_kwargs["wallet"]
        assert created_wallet.wallet_address == normalized_wallet_address
        assert created_wallet.chain_type == chain_type
        assert created_wallet.network_name == network_name
        assert created_wallet.token_symbol == token_symbol
        assert created_wallet.chain_id == chain_id
        assert created_wallet.verified_at == fixed_now
        assert created_wallet.is_active is True
        assert created_wallet.is_permitted is True

        mock_store_repository.create_store_wallet.assert_called_once()
        create_store_wallet_kwargs = mock_store_repository.create_store_wallet.call_args.kwargs
        assert create_store_wallet_kwargs["mysql_session"] is mysql_session
        created_store_wallet = create_store_wallet_kwargs["store_wallet"]
        assert created_store_wallet.store_id == store_id
        assert created_store_wallet.wallet_id == 77

        mock_nonce_repository.update_nonce.assert_called_once_with(
            mysql_session=mysql_session,
            nonce=nonce_entity,
        )
        assert nonce_entity.used_at == fixed_now
        assert result == WalletVerifyResponse(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            token_symbol=token_symbol,
            chain_id=chain_id,
            is_active=True,
            is_permitted=True,
            verified_at="2026-04-12 12:34",
        )

    @patch("app.services.store_service.StoreRepository")
    def test_create_store_wallet_conflict(self, mock_repository_class):
        """同一チェーン・ネットワークに同じウォレットが存在する場合は競合例外を送出する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        token_symbol = "JPYC"
        chain_id = 11155111
        nonce_entity = SimpleNamespace(used_at=None)

        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_store_id.return_value = SimpleNamespace(wallet_id=99)

        with pytest.raises(WalletConflictException):
            StoreService().create_store_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                token_symbol=token_symbol,
                chain_id=chain_id,
                nonce_entity=nonce_entity,
            )

        mock_repository.get_wallet_by_store_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )
        mock_repository.create_wallet.assert_not_called()
        mock_repository.create_store_wallet.assert_not_called()
        mock_repository.update_nonce.assert_not_called()
        assert nonce_entity.used_at is None
