from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
    UnauthorizedException,
    WalletConflictException,
)
from app.models.responses.wallet_response import WalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.services.store_service import JST, StoreService


NOW = datetime(2026, 4, 12, 12, 0, 0)


class TestGetStoreWallet:
    @patch("app.services.store_service.StoreRepository")
    def test_get_store_wallet(self, mock_repository_class) -> None:
        session = Mock()
        store_id = 10
        wallet_info = SimpleNamespace(
            wallet_id=201,
            wallet_address="0x2222222222222222222222222222222222222222",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            verified_at=datetime(2024, 2, 10, 12, 0, 0),
            created_at=datetime(2024, 2, 1, 9, 30, 0),
            updated_at=datetime(2024, 2, 15, 18, 45, 0),
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = wallet_info

        result = StoreService().get_store_wallet(session=session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            session=session,
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
            verified_at="2024-02-10 12:00",
            created_at="2024-02-01 09:30",
            updated_at="2024-02-15 18:45",
        )

    @patch("app.services.store_service.StoreRepository")
    def test_get_store_wallet_returns_none_when_wallet_not_found(self, mock_repository_class) -> None:
        session = Mock()
        store_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = None

        result = StoreService().get_store_wallet(session=session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            session=session,
            store_id=store_id,
        )
        assert result is None


class TestCreateWalletNonce:
    """StoreService の create_wallet_nonce を検証するテスト。"""

    @patch("app.services.store_service.secrets.token_urlsafe", return_value="generated-nonce")
    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.NonceRepository")
    def test_create_wallet_nonce(self, mock_nonce_repository_class, mock_store_repository_class, mock_token_urlsafe):
        """nonce を生成して保存し、レスポンスへ整形することを検証する。"""
        session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_by_id.return_value = SimpleNamespace(store_id=store_id)

        mock_nonce_repository = mock_nonce_repository_class.return_value
        mock_nonce_repository.create_nonce.side_effect = lambda session, nonce: SimpleNamespace(nonce_id=123, nonce=nonce.nonce)

        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreService().create_wallet_nonce(
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_store_repository.get_store_by_id.assert_called_once_with(
            session=session,
            store_id=store_id,
        )
        mock_token_urlsafe.assert_called_once_with(32)
        mock_nonce_repository.create_nonce.assert_called_once()
        mock_store_repository.create_store_nonce.assert_called_once()

        nonce_kwargs = mock_nonce_repository.create_nonce.call_args.kwargs
        assert nonce_kwargs["session"] is session
        created_nonce = nonce_kwargs["nonce"]
        assert created_nonce.wallet_address == wallet_address.lower()
        assert created_nonce.chain_type == chain_type
        assert created_nonce.network_name == network_name
        assert created_nonce.nonce == "generated-nonce"
        assert created_nonce.expires_at == fixed_now + timedelta(minutes=10)

        store_nonce_kwargs = mock_store_repository.create_store_nonce.call_args.kwargs
        assert store_nonce_kwargs["session"] is session
        created_store_nonce = store_nonce_kwargs["store_nonce"]
        assert created_store_nonce.store_id == store_id
        assert created_store_nonce.nonce_id == 123
        assert result == WalletNonceCreateResponse(
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

    @patch("app.services.store_service.WalletUtil.recover_address")
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
    @patch("app.services.store_service.WalletRepository")
    @patch("app.services.store_service.NonceRepository")
    def test_create_store_wallet(self, mock_nonce_repository_class, mock_wallet_repository_class, mock_store_repository_class):
        """primary の切り替えと nonce の使用済み更新を行い、レスポンスを返すことを検証する。"""
        session = Mock()
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
                session=session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                token_symbol=token_symbol,
                chain_id=chain_id,
                nonce_entity=nonce_entity,
            )

        mock_store_repository.get_wallet_by_store_id.assert_called_once_with(
            session=session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )

        mock_wallet_repository.create_wallet.assert_called_once()
        create_wallet_kwargs = mock_wallet_repository.create_wallet.call_args.kwargs
        assert create_wallet_kwargs["session"] is session
        created_wallet = create_wallet_kwargs["wallet"]
        assert created_wallet.wallet_address == normalized_wallet_address
        assert created_wallet.chain_type == chain_type
        assert created_wallet.network_name == network_name
        assert created_wallet.token_symbol == token_symbol
        assert created_wallet.chain_id == chain_id
        assert created_wallet.verified_at == fixed_now
        assert created_wallet.is_active is True

        mock_store_repository.create_store_wallet.assert_called_once()
        create_store_wallet_kwargs = mock_store_repository.create_store_wallet.call_args.kwargs
        assert create_store_wallet_kwargs["session"] is session
        created_store_wallet = create_store_wallet_kwargs["store_wallet"]
        assert created_store_wallet.store_id == store_id
        assert created_store_wallet.wallet_id == 77

        mock_nonce_repository.update_nonce.assert_called_once_with(
            session=session,
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
        token_symbol = "JPYC"
        chain_id = 11155111
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
                token_symbol=token_symbol,
                chain_id=chain_id,
                nonce_entity=nonce_entity,
            )

        mock_repository.get_wallet_by_store_id.assert_called_once_with(
            session=session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )
        mock_repository.create_wallet.assert_not_called()
        mock_repository.create_store_wallet.assert_not_called()
        mock_repository.update_nonce.assert_not_called()
        assert nonce_entity.used_at is None


class TestDeleteWallet:
    """StoreService の delete_wallet を検証するテスト。"""

    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.WalletRepository")
    def test_delete_wallet(self, mock_wallet_repository_class, mock_store_repository_class):
        """WalletRepository と StoreRepository の各削除メソッドが正しい引数で呼ばれることを検証する。"""
        session = Mock()
        wallet_id = 42

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_store_repository = mock_store_repository_class.return_value

        StoreService().delete_wallet(session=session, wallet_id=wallet_id)

        mock_wallet_repository.delete_wallet_by_wallet_id.assert_called_once_with(
            session=session,
            wallet_id=wallet_id,
        )
        mock_store_repository.delete_store_wallet_by_wallet_id.assert_called_once_with(
            session=session,
            wallet_id=wallet_id,
        )

    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.WalletRepository")
    def test_delete_wallet_store_repository_not_called_when_wallet_repository_raises(
        self,
        mock_wallet_repository_class,
        mock_store_repository_class,
    ):
        """WalletRepository が例外を送出した場合、StoreRepository は呼ばれないことを検証する。"""
        session = Mock()
        wallet_id = 42

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_store_repository = mock_store_repository_class.return_value
        mock_wallet_repository.delete_wallet_by_wallet_id.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            StoreService().delete_wallet(session=session, wallet_id=wallet_id)

        mock_wallet_repository.delete_wallet_by_wallet_id.assert_called_once_with(
            session=session,
            wallet_id=wallet_id,
        )
        mock_store_repository.delete_store_wallet_by_wallet_id.assert_not_called()
