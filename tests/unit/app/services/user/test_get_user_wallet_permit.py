from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.responses.wallet_permit_response import WalletPermitResponse
from app.services.user_service import UserService


class TestGetUserWalletPermit:
    """get_user_wallet_permit の動作を検証する。"""

    @patch("app.services.user_service.get_wallet_permit_config")
    @patch("app.services.user_service.UserRepository")
    def test_get_user_wallet_permit(
        self,
        mock_repository_class,
        mock_get_wallet_permit_config,
    ) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        user_id = 101
        wallet_info = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=11155111,
            token_symbol="JPYC",
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_wallet.return_value = wallet_info
        mock_get_wallet_permit_config.return_value = SimpleNamespace(
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )

        result = UserService().get_user_wallet_permit(mysql_session=mysql_session, user_id=user_id)

        mock_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_get_wallet_permit_config.assert_called_once_with(chain_id=11155111)
        assert result == WalletPermitResponse(
            wallet_address=wallet_info.wallet_address,
            chain_id=11155111,
            token_symbol="JPYC",
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )

    @patch("app.services.user_service.get_wallet_permit_config")
    @patch("app.services.user_service.UserRepository")
    def test_get_user_wallet_permit_returns_none_when_wallet_not_found(
        self,
        mock_repository_class,
        mock_get_wallet_permit_config,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        user_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_wallet.return_value = None

        result = UserService().get_user_wallet_permit(mysql_session=mysql_session, user_id=user_id)

        mock_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_get_wallet_permit_config.assert_not_called()
        assert result is None
