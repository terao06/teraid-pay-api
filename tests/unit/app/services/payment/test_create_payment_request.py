from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    WalletNotPermittedException,
    WalletNotFoundException,
)
from app.models.mysql.payment_request import PaymentRequest
from app.services.payment_service import JST, PaymentService


class TestCreatePaymentRequest:
    """PaymentService.create_payment_request の単体テスト。"""

    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    @patch("app.services.payment_service.datetime")
    def test_create_payment_request(
        self,
        mock_datetime,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
    ) -> None:
        """wallet 情報から決済リクエストを作成し、repository に保存できることを検証する。"""
        mysql_session = Mock()
        store_id = 101
        user_id = 102
        amount = 1500
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)
        store_wallet = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            token_symbol="JPYC",
            chain_id=11155111,
        )
        user_wallet = SimpleNamespace(
            wallet_address="0x2222222222222222222222222222222222222222",
            token_symbol="JPYC",
            chain_id=11155111,
            is_permitted=True,
        )

        mock_datetime.now.return_value = fixed_now
        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet
        mock_payment_repository = mock_payment_repository_class.return_value
        saved_payment_request_id = 501

        def create_payment_request(mysql_session, payment_request):
            payment_request.payment_request_id = saved_payment_request_id
            return payment_request

        mock_payment_repository.create_payment_request.side_effect = create_payment_request

        result = PaymentService().create_payment_request(
            mysql_session=mysql_session,
            store_id=store_id,
            user_id=user_id,
            amount=amount,
        )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_user_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_payment_repository.create_payment_request.assert_called_once()

        payment_request_kwargs = mock_payment_repository.create_payment_request.call_args.kwargs
        assert payment_request_kwargs["mysql_session"] is mysql_session
        created_payment_request = payment_request_kwargs["payment_request"]
        assert isinstance(created_payment_request, PaymentRequest)
        assert created_payment_request.store_id == store_id
        assert created_payment_request.user_id == user_id
        assert created_payment_request.store_wallet_address == store_wallet.wallet_address
        assert created_payment_request.user_wallet_address == user_wallet.wallet_address
        assert created_payment_request.amount == amount
        assert created_payment_request.token_symbol == store_wallet.token_symbol
        assert created_payment_request.chain_id == store_wallet.chain_id
        assert created_payment_request.status is None
        assert created_payment_request.transaction_hash is None
        assert created_payment_request.expires_at == fixed_now + timedelta(minutes=10)
        assert result == saved_payment_request_id

    @pytest.mark.parametrize(
        ("store_wallet", "user_wallet"),
        [
            (
                None,
                SimpleNamespace(
                    wallet_address="0x2222222222222222222222222222222222222222",
                    token_symbol="JPYC",
                    chain_id=11155111,
                    is_permitted=True,
                ),
            ),
            (
                SimpleNamespace(
                    wallet_address="0x1111111111111111111111111111111111111111",
                    token_symbol="JPYC",
                    chain_id=11155111,
                ),
                None,
            ),
        ],
        ids=["store-wallet-not-found", "user-wallet-not-found"],
    )
    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    def test_create_payment_request_raises_when_wallet_not_found(
        self,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
        store_wallet,
        user_wallet,
    ) -> None:
        """store/user の wallet が取得できない場合は WalletNotFoundException を送出する。"""
        mysql_session = Mock()

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet

        with pytest.raises(WalletNotFoundException):
            PaymentService().create_payment_request(
                mysql_session=mysql_session,
                store_id=101,
                user_id=102,
                amount=1500,
            )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )
        if store_wallet is None:
            mock_user_repository.get_user_wallet.assert_not_called()
        else:
            mock_user_repository.get_user_wallet.assert_called_once_with(
                mysql_session=mysql_session,
                user_id=102,
            )
        mock_payment_repository_class.assert_not_called()

    @pytest.mark.parametrize(
        "user_wallet",
        [
            SimpleNamespace(
                wallet_address="0x2222222222222222222222222222222222222222",
                token_symbol="USDC",
                chain_id=11155111,
                is_permitted=True,
            ),
            SimpleNamespace(
                wallet_address="0x2222222222222222222222222222222222222222",
                token_symbol="JPYC",
                chain_id=137,
                is_permitted=True,
            ),
        ],
        ids=["token-mismatch", "chain-mismatch"],
    )
    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    def test_create_payment_request_raises_when_wallet_values_mismatch(
        self,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
        user_wallet,
    ) -> None:
        """store/user の token または chain が一致しない場合は ValueError を送出する。"""
        mysql_session = Mock()
        store_wallet = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            token_symbol="JPYC",
            chain_id=11155111,
        )

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet

        with pytest.raises(ValueError):
            PaymentService().create_payment_request(
                mysql_session=mysql_session,
                store_id=101,
                user_id=102,
                amount=1500,
            )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )
        mock_user_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=102,
        )
        mock_payment_repository_class.assert_not_called()

    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    def test_create_payment_request_raises_when_user_wallet_permit_is_incomplete(
        self,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
    ) -> None:
        """user wallet の permit 許可が未完了の場合は payment request を作成しないことを検証する。"""
        mysql_session = Mock()
        store_wallet = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            token_symbol="JPYC",
            chain_id=11155111,
        )
        user_wallet = SimpleNamespace(
            wallet_address="0x2222222222222222222222222222222222222222",
            token_symbol="JPYC",
            chain_id=11155111,
            is_permitted=False,
        )

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet

        with pytest.raises(WalletNotPermittedException):
            PaymentService().create_payment_request(
                mysql_session=mysql_session,
                store_id=101,
                user_id=102,
                amount=1500,
            )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )
        mock_user_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=102,
        )
        mock_payment_repository_class.assert_not_called()
