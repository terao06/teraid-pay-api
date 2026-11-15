from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.responses.wallet_response import WalletResponse
from app.services.user_service import UserService


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
            is_permitted=False,
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
            is_permitted=False,
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
