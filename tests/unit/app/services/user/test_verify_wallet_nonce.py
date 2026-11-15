from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    UnauthorizedException,
    UserNotFoundException,
)
from app.services.user_service import UserService


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
