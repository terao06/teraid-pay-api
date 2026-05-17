from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    UnauthorizedException,
    UserNotFoundException,
    WalletConflictException,
    WalletNotFoundException,
)
from app.models.mysql.wallet import Wallet
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_approval_response import WalletApprovalResponse
from app.models.responses.wallet_response import WalletResponse
from app.services.user_service import JST, UserService


class TestGetUserWallet:
    """get_user_wallet の単体テスト。"""

    @patch("app.services.user_service.UserRepository")
    def test_get_user_wallet(self, mock_repository_class) -> None:
        """repository の取得結果をレスポンスモデルへ整形できることを確認する。"""
        mysql_session = Mock()
        user_id = 101
        wallet_info = SimpleNamespace(
            wallet_id=301,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_approval=False,
            verified_at=datetime(2024, 1, 10, 12, 0, 0),
            created_at=datetime(2024, 1, 1, 9, 30, 0),
            updated_at=datetime(2024, 1, 15, 18, 45, 0),
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_wallet.return_value = wallet_info

        result = UserService().get_user_wallet(mysql_session=mysql_session, user_id=user_id)

        mock_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        assert result == WalletResponse(
            wallet_id=301,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_approval=False,
            verified_at="2024-01-10 12:00",
            created_at="2024-01-01 09:30",
            updated_at="2024-01-15 18:45",
        )

    @patch("app.services.user_service.UserRepository")
    def test_get_user_wallet_returns_none_when_wallet_not_found(self, mock_repository_class) -> None:
        """repository が未検出を返した場合に None を返すことを確認する。"""
        mysql_session = Mock()
        user_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_wallet.return_value = None

        result = UserService().get_user_wallet(mysql_session=mysql_session, user_id=user_id)

        mock_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        assert result is None


class TestGetUserWalletApproval:
    @patch("app.services.user_service.get_wallet_approval_config")
    @patch("app.services.user_service.UserRepository")
    def test_get_user_wallet_approval(
        self,
        mock_repository_class,
        mock_get_wallet_approval_config,
    ) -> None:
        mysql_session = Mock()
        user_id = 101
        wallet_info = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=11155111,
            token_symbol="JPYC",
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_wallet.return_value = wallet_info
        mock_get_wallet_approval_config.return_value = SimpleNamespace(
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )

        result = UserService().get_user_wallet_approval(mysql_session=mysql_session, user_id=user_id)

        mock_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_get_wallet_approval_config.assert_called_once_with(chain_id=11155111)
        assert result == WalletApprovalResponse(
            wallet_address=wallet_info.wallet_address,
            chain_id=11155111,
            token_symbol="JPYC",
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )

    @patch("app.services.user_service.get_wallet_approval_config")
    @patch("app.services.user_service.UserRepository")
    def test_get_user_wallet_approval_returns_none_when_wallet_not_found(
        self,
        mock_repository_class,
        mock_get_wallet_approval_config,
    ) -> None:
        mysql_session = Mock()
        user_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_wallet.return_value = None

        result = UserService().get_user_wallet_approval(mysql_session=mysql_session, user_id=user_id)

        mock_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_get_wallet_approval_config.assert_not_called()
        assert result is None


class TestUpdateWalletApprovalState:
    @patch("app.services.user_service.WalletRepository")
    def test_update_wallet_approval_state(
        self,
        mock_repository_class,
    ) -> None:
        mysql_session = Mock()
        wallet_id = 301
        wallet_info = SimpleNamespace(
            wallet_id=wallet_id,
            wallet_address="0x1111111111111111111111111111111111111111",
            is_approval=False,
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_id.return_value = wallet_info

        result = UserService().update_wallet_approval_state(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )

        mock_repository.get_wallet_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        assert wallet_info.is_approval is True
        mock_repository.update_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            wallet=wallet_info,
        )
        assert result is None

    @patch("app.services.user_service.WalletRepository")
    def test_update_wallet_approval_state_wallet_not_found(
        self,
        mock_repository_class,
    ) -> None:
        mysql_session = Mock()
        wallet_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_id.return_value = None

        with pytest.raises(WalletNotFoundException):
            UserService().update_wallet_approval_state(
                mysql_session=mysql_session,
                wallet_id=wallet_id,
            )

        mock_repository.get_wallet_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_repository.update_wallet.assert_not_called()

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


class TestVerifyWalletNonce:
    """verify_wallet_nonce の単体テスト。"""

    @patch("app.services.user_service.WalletUtil.recover_address")
    @patch("app.services.user_service.UserRepository")
    def test_verify_wallet_nonce(
        self,
        mock_repository_class,
        mock_recover_address,
    ) -> None:
        """正常な署名と利用可能 nonce がある場合に nonce エンティティを返すことを検証する。"""
        mysql_session = Mock()
        user_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        normalized_wallet_address = wallet_address.lower()
        signature = "signed-message"
        chain_type = "ethereum"
        network_name = "sepolia"
        nonce_entity = SimpleNamespace(nonce="available-nonce")

        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_by_id.return_value = SimpleNamespace(user_id=user_id)
        mock_repository.get_latest_available_nonce.return_value = nonce_entity
        mock_recover_address.return_value = normalized_wallet_address

        result = UserService().verify_wallet_nonce(
            mysql_session=mysql_session,
            user_id=user_id,
            wallet_address=wallet_address,
            signature=signature,
            chain_type=chain_type,
            network_name=network_name,
        )

        mock_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_repository.get_latest_available_nonce.assert_called_once()
        latest_nonce_kwargs = mock_repository.get_latest_available_nonce.call_args.kwargs
        assert latest_nonce_kwargs["mysql_session"] is mysql_session
        assert latest_nonce_kwargs["user_id"] == user_id
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
            "user",
            "nonce_entity",
            "recovered_address",
            "expected_exception",
        ),
        [
            (
                None,
                SimpleNamespace(nonce="available-nonce"),
                "0xabcdef1234567890abcdef1234567890abcdef12",
                UserNotFoundException,
            ),
            (
                SimpleNamespace(user_id=10),
                None,
                "0xabcdef1234567890abcdef1234567890abcdef12",
                UnauthorizedException,
            ),
            (
                SimpleNamespace(user_id=10),
                SimpleNamespace(nonce="available-nonce"),
                "0x0000000000000000000000000000000000000000",
                UnauthorizedException,
            ),
        ],
        ids=[
            "user-not-found",
            "nonce-not-found",
            "signature-mismatch",
        ],
    )
    @patch("app.services.user_service.WalletUtil.recover_address")
    @patch("app.services.user_service.UserRepository")
    def test_verify_wallet_nonce_raises(
        self,
        mock_repository_class,
        mock_recover_address,
        user,
        nonce_entity,
        recovered_address,
        expected_exception,
    ) -> None:
        """異常系で適切な例外を送出することを検証する。"""
        mysql_session = Mock()
        user_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        signature = "signed-message"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_by_id.return_value = user
        mock_repository.get_latest_available_nonce.return_value = nonce_entity
        mock_recover_address.return_value = recovered_address

        with pytest.raises(expected_exception):
            UserService().verify_wallet_nonce(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=wallet_address,
                signature=signature,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )

        if user is None:
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
