from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
    UnauthorizedException,
)
from app.services.store_service import StoreService


class TestVerifyWalletNonce:
    """StoreService の verify_wallet_nonce を検証するテスト。"""

    @patch("app.services.store_service.WalletUtil.recover_address")
    @patch("app.services.store_service.StoreRepository")
    def test_verify_wallet_nonce(
        self,
        mock_repository_class,
        mock_recover_address,
    ):
        """正常な署名と利用可能 nonce がある場合に nonce エンティティを返すことを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        normalized_wallet_address = wallet_address.lower()
        signature = "signed-message"
        chain_type = "ethereum"
        network_name = "sepolia"
        nonce_entity = SimpleNamespace(nonce="available-nonce")

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = SimpleNamespace(store_id=10)
        mock_repository.get_latest_available_nonce.return_value = nonce_entity
        mock_recover_address.return_value = normalized_wallet_address

        result = StoreService().verify_wallet_nonce(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_address=wallet_address,
            signature=signature,
            chain_type=chain_type,
            network_name=network_name,
        )

        mock_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_repository.get_latest_available_nonce.assert_called_once()
        latest_nonce_kwargs = mock_repository.get_latest_available_nonce.call_args.kwargs
        assert latest_nonce_kwargs["mysql_session"] is mysql_session
        assert latest_nonce_kwargs["store_id"] == store_id
        assert latest_nonce_kwargs["wallet_address"] == normalized_wallet_address
        assert latest_nonce_kwargs["chain_type"] == chain_type
        assert latest_nonce_kwargs["network_name"] == network_name
        assert isinstance(latest_nonce_kwargs["expires_at"], datetime)

        mock_recover_address.assert_called_once_with(
            message=nonce_entity.nonce,
            signature=signature,
        )
        assert result == nonce_entity

    @pytest.mark.parametrize(
        (
            "store",
            "nonce_entity",
            "recovered_address",
            "expected_exception",
        ),
        [
            (
                None,
                SimpleNamespace(nonce="available-nonce"),
                "0xabcdef1234567890abcdef1234567890abcdef12",
                StoreNotFoundException,
            ),
            (
                SimpleNamespace(store_id=10),
                None,
                "0xabcdef1234567890abcdef1234567890abcdef12",
                UnauthorizedException,
            ),
            (
                SimpleNamespace(store_id=10),
                SimpleNamespace(nonce="available-nonce"),
                "0x0000000000000000000000000000000000000000",
                UnauthorizedException,
            ),
        ],
        ids=[
            "store-not-found",
            "nonce-not-found",
            "signature-mismatch",
        ],
    )
    @patch("app.services.store_service.WalletUtil.recover_address")
    @patch("app.services.store_service.StoreRepository")
    def test_verify_wallet_nonce_raises(
        self,
        mock_repository_class,
        mock_recover_address,
        store,
        nonce_entity,
        recovered_address,
        expected_exception,
    ):
        """異常系では条件に応じた例外を送出することを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        signature = "signed-message"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = store
        mock_repository.get_latest_available_nonce.return_value = nonce_entity
        mock_recover_address.return_value = recovered_address

        with pytest.raises(expected_exception):
            StoreService().verify_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                signature=signature,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )

        if store is None:
            mock_repository.get_latest_available_nonce.assert_not_called()
            mock_recover_address.assert_not_called()
            return

        mock_repository.get_latest_available_nonce.assert_called_once()

        if nonce_entity is None:
            mock_recover_address.assert_not_called()
            return

        mock_recover_address.assert_called_once_with(
            message=nonce_entity.nonce,
            signature=signature,
        )
