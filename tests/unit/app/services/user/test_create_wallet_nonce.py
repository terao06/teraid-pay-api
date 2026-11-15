from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    UserNotFoundException,
    WalletConflictException,
)
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.services.user_service import JST, UserService


class TestCreateWalletNonce:
    """create_wallet_nonce の単体テスト。"""

    @patch("app.services.user_service.secrets.token_urlsafe", return_value="generated-nonce")
    @patch("app.services.user_service.UserRepository")
    @patch("app.services.user_service.NonceRepository")
    @patch("app.services.user_service.WalletRepository")
    def test_create_wallet_nonce(
        self,
        mock_wallet_repository_class,
        mock_nonce_repository_class,
        mock_user_repository_class,
        mock_token_urlsafe,
    ) -> None:
        """nonce を生成して user_nonce を作成し、レスポンスへ整形することを検証する。"""
        mysql_session = Mock()
        user_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = SimpleNamespace(user_id=user_id)

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.get_wallet_by_address.return_value = None

        mock_nonce_repository = mock_nonce_repository_class.return_value
        mock_nonce_repository.create_nonce.side_effect = (
            lambda mysql_session, nonce: SimpleNamespace(nonce_id=123, nonce=nonce.nonce)
        )

        with patch("app.services.user_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = UserService().create_wallet_nonce(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_wallet_repository.get_wallet_by_address.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_address=wallet_address,
        )
        mock_token_urlsafe.assert_called_once_with(32)
        mock_nonce_repository.create_nonce.assert_called_once()
        mock_user_repository.create_user_nonce.assert_called_once()

        nonce_kwargs = mock_nonce_repository.create_nonce.call_args.kwargs
        assert nonce_kwargs["mysql_session"] is mysql_session
        created_nonce = nonce_kwargs["nonce"]
        assert created_nonce.wallet_address == wallet_address.lower()
        assert created_nonce.chain_type == chain_type
        assert created_nonce.network_name == network_name
        assert created_nonce.nonce == "generated-nonce"
        assert created_nonce.expires_at == fixed_now + timedelta(minutes=10)

        user_nonce_kwargs = mock_user_repository.create_user_nonce.call_args.kwargs
        assert user_nonce_kwargs["mysql_session"] is mysql_session
        created_user_nonce = user_nonce_kwargs["user_nonce"]
        assert created_user_nonce.user_id == user_id
        assert created_user_nonce.nonce_id == 123
        assert result == WalletNonceCreateResponse(
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

    @patch("app.services.user_service.WalletRepository")
    @patch("app.services.user_service.UserRepository")
    def test_create_wallet_nonce_not_found_error(
        self,
        mock_repository_class,
        mock_wallet_repository_class,
    ) -> None:
        """ユーザーが存在しない場合に UserNotFoundException を送出することを検証する。"""
        mysql_session = Mock()
        user_id = 999
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_by_id.return_value = None

        with pytest.raises(UserNotFoundException):
            UserService().create_wallet_nonce(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_wallet_repository_class.return_value.get_wallet_by_address.assert_not_called()
        mock_repository.create_user_nonce.assert_not_called()

    @patch("app.services.user_service.secrets.token_urlsafe")
    @patch("app.services.user_service.UserRepository")
    @patch("app.services.user_service.NonceRepository")
    @patch("app.services.user_service.WalletRepository")
    def test_create_wallet_nonce_wallet_conflict_error(
        self,
        mock_wallet_repository_class,
        mock_nonce_repository_class,
        mock_user_repository_class,
        mock_token_urlsafe,
    ) -> None:
        """ウォレットが既に存在する場合に WalletConflictException を送出することを検証する。"""
        mysql_session = Mock()
        user_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = SimpleNamespace(user_id=user_id)

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.get_wallet_by_address.return_value = SimpleNamespace(wallet_id=1)

        with pytest.raises(WalletConflictException):
            UserService().create_wallet_nonce(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_wallet_repository.get_wallet_by_address.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_address=wallet_address,
        )
        mock_token_urlsafe.assert_not_called()
        mock_nonce_repository_class.return_value.create_nonce.assert_not_called()
        mock_user_repository.create_user_nonce.assert_not_called()
