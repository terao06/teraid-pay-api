from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
    UnauthorizedException,
    WalletConflictException,
)
from app.core.utils.wallet import WalletUtil
from app.models.responses.store_wallet_response import StoreWalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import StoreWalletVerifyResponse
from app.services.store_service import JST, StoreService


NOW = datetime(2026, 4, 12, 12, 0, 0)


class TestGetStoreWalletList:
    """StoreService の get_store_wallet_list を検証するテスト。"""

    @pytest.mark.parametrize(
        ("repository_result", "expected"),
        [
            (
                SimpleNamespace(
                    store_wallet_id=1,
                    store_id=10,
                    wallet_address="wallet-address-1",
                    chain_type="ETH",
                    network_name="mainnet",
                    is_active=True,
                    verified_at=NOW,
                    created_at=NOW,
                    updated_at=NOW,
                ),
                StoreWalletResponse(
                    store_wallet_id=1,
                    store_id=10,
                    wallet_address="wallet-address-1",
                    chain_type="ETH",
                    network_name="mainnet",
                    is_active=True,
                    verified_at=NOW.strftime("%Y-%m-%d %H:%M"),
                    created_at=NOW.strftime("%Y-%m-%d %H:%M"),
                    updated_at=NOW.strftime("%Y-%m-%d %H:%M"),
                ),
            ),
            (None, None),
        ],
    )
    @patch("app.services.store_service.StoreRepository")
    def test_get_store_wallet(self, mock_repository_class, repository_result, expected):
        """リポジトリ結果を StoreWalletResponse の一覧へ整形して返すことを検証する。"""
        session = Mock()
        store_id = 10
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = repository_result

        result = StoreService().get_store_wallet(session=session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            session=session,
            store_id=store_id,
        )
        assert result == expected


class TestCreateWalletNonce:
    """StoreService の create_wallet_nonce を検証するテスト。"""

    @patch("app.services.store_service.secrets.token_urlsafe", return_value="generated-nonce")
    @patch("app.services.store_service.StoreRepository")
    def test_create_wallet_nonce(self, mock_repository_class, mock_token_urlsafe):
        """nonce を生成して保存し、レスポンスへ整形することを検証する。"""
        session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = SimpleNamespace(store_id=store_id)
        mock_repository.create_nonce.side_effect = lambda session, nonce: SimpleNamespace(nonce_id=123, nonce=nonce.nonce)

        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreService().create_wallet_nonce(
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_store_by_id.assert_called_once_with(
            session=session,
            store_id=store_id,
        )
        mock_token_urlsafe.assert_called_once_with(32)
        mock_repository.create_nonce.assert_called_once()
        mock_repository.create_store_nonce.assert_called_once()

        nonce_kwargs = mock_repository.create_nonce.call_args.kwargs
        assert nonce_kwargs["session"] is session
        created_nonce = nonce_kwargs["nonce"]
        assert created_nonce.wallet_address == wallet_address.lower()
        assert created_nonce.chain_type == chain_type
        assert created_nonce.network_name == network_name
        assert created_nonce.nonce == "generated-nonce"
        assert created_nonce.expires_at == fixed_now + timedelta(minutes=10)

        store_nonce_kwargs = mock_repository.create_store_nonce.call_args.kwargs
        assert store_nonce_kwargs["session"] is session
        created_store_nonce = store_nonce_kwargs["store_nonce"]
        assert created_store_nonce.store_id == store_id
        assert created_store_nonce.nonce_id == 123
        assert result == WalletNonceCreateResponse(
            message=WalletUtil.build_sign_message(
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                nonce="generated-nonce",
            ),
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

    @patch("app.services.store_service.StoreRepository")
    def test_create_wallet_nonce_not_found_error(self, mock_repository_class):
        """店舗が存在しない場合に StoreNotFoundException を送出することを検証する。"""
        session = Mock()
        store_id = 999
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = None

        with pytest.raises(StoreNotFoundException):
            StoreService().create_wallet_nonce(
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_store_by_id.assert_called_once_with(
            session=session,
            store_id=store_id,
        )
        mock_repository.create_nonce.assert_not_called()
        mock_repository.create_store_nonce.assert_not_called()


class TestVerifyWalletNonce:
    """StoreService の verify_wallet_nonce を検証するテスト。"""

    @patch.object(StoreService, "_recover_address")
    @patch("app.services.store_service.StoreRepository")
    def test_verify_wallet_nonce(
        self,
        mock_repository_class,
        mock_recover_address,
    ):
        """正常な署名と利用可能 nonce がある場合に nonce エンティティを返すことを検証する。"""
        session = Mock()
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
            session=session,
            store_id=store_id,
            wallet_address=wallet_address,
            signature=signature,
            chain_type=chain_type,
            network_name=network_name,
        )

        mock_repository.get_store_by_id.assert_called_once_with(
            session=session,
            store_id=store_id,
        )
        mock_repository.get_latest_available_nonce.assert_called_once()
        latest_nonce_kwargs = mock_repository.get_latest_available_nonce.call_args.kwargs
        assert latest_nonce_kwargs["session"] is session
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
    @patch.object(StoreService, "_recover_address")
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
        session = Mock()
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
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                signature=signature,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_store_by_id.assert_called_once_with(
            session=session,
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


class TestCreateStoreWallet:
    """StoreService の create_store_wallet を検証するテスト。"""

    @patch("app.services.store_service.StoreRepository")
    def test_create_store_wallet(self, mock_repository_class):
        """primary の切り替えと nonce の使用済み更新を行い、レスポンスを返すことを検証する。"""
        session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        normalized_wallet_address = wallet_address.lower()
        chain_type = "ethereum"
        network_name = "sepolia"
        fixed_now = datetime(2026, 4, 12, 12, 34, 56)
        nonce_entity = SimpleNamespace(used_at=None)

        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_store_id.return_value = None
        mock_repository.create_wallet.return_value = SimpleNamespace(wallet_id=77)

        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreService().create_store_wallet(
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                nonce_entity=nonce_entity,
            )

        mock_repository.get_wallet_by_store_id.assert_called_once_with(
            session=session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
        )

        mock_repository.create_wallet.assert_called_once()
        create_wallet_kwargs = mock_repository.create_wallet.call_args.kwargs
        assert create_wallet_kwargs["session"] is session
        created_wallet = create_wallet_kwargs["wallet"]
        assert created_wallet.wallet_address == normalized_wallet_address
        assert created_wallet.chain_type == chain_type
        assert created_wallet.network_name == network_name
        assert created_wallet.verified_at == fixed_now
        assert created_wallet.is_active is True

        mock_repository.create_store_wallet.assert_called_once()
        create_store_wallet_kwargs = mock_repository.create_store_wallet.call_args.kwargs
        assert create_store_wallet_kwargs["session"] is session
        created_store_wallet = create_store_wallet_kwargs["store_wallet"]
        assert created_store_wallet.store_id == store_id
        assert created_store_wallet.wallet_id == 77

        mock_repository.update_store_wallet_nonce.assert_called_once_with(
            session=session,
            nonce=nonce_entity,
        )
        assert nonce_entity.used_at == fixed_now
        assert result == StoreWalletVerifyResponse(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            is_active=True,
            verified_at="2026-04-12 12:34",
        )

    @patch("app.services.store_service.StoreRepository")
    def test_create_store_wallet_conflict(self, mock_repository_class):
        """同一チェーン・ネットワークに同じウォレットが存在する場合は競合例外を送出する。"""
        session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        nonce_entity = SimpleNamespace(used_at=None)

        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_store_id.return_value = SimpleNamespace(wallet_id=99)

        with pytest.raises(WalletConflictException):
            StoreService().create_store_wallet(
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                nonce_entity=nonce_entity,
            )

        mock_repository.get_wallet_by_store_id.assert_called_once_with(
            session=session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
        )
        mock_repository.create_wallet.assert_not_called()
        mock_repository.create_store_wallet.assert_not_called()
        mock_repository.update_store_wallet_nonce.assert_not_called()
        assert nonce_entity.used_at is None


class TestRecoverAddress:
    """StoreService の _recover_address を検証するテスト。"""

    @patch("app.services.store_service.Account.recover_message")
    @patch("app.services.store_service.encode_defunct")
    def test_recover_address_returns_recovered_wallet_address(
        self,
        mock_encode_defunct,
        mock_recover_message,
    ) -> None:
        """署名復元に成功した場合は復元されたウォレットアドレスを返す。"""
        message = "sign this message"
        signature = "0xsigned"
        encoded_message = Mock()
        recovered_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"

        mock_encode_defunct.return_value = encoded_message
        mock_recover_message.return_value = recovered_address

        result = StoreService._recover_address(
            message=message,
            signature=signature,
        )

        mock_encode_defunct.assert_called_once_with(text=message)
        mock_recover_message.assert_called_once_with(
            encoded_message,
            signature=signature,
        )
        assert result == recovered_address

    @patch("app.services.store_service.Account.recover_message")
    @patch("app.services.store_service.encode_defunct")
    def test_recover_address_raises_unauthorized_when_recover_fails(
        self,
        mock_encode_defunct,
        mock_recover_message,
    ) -> None:
        """署名復元で例外が発生した場合は UnauthorizedException へ変換する。"""
        message = "sign this message"
        signature = "0xinvalid"
        encoded_message = Mock()

        mock_encode_defunct.return_value = encoded_message
        mock_recover_message.side_effect = Exception("recover failed")

        with pytest.raises(UnauthorizedException):
            StoreService._recover_address(
                message=message,
                signature=signature,
            )

        mock_encode_defunct.assert_called_once_with(text=message)
        mock_recover_message.assert_called_once_with(
            encoded_message,
            signature=signature,
        )
