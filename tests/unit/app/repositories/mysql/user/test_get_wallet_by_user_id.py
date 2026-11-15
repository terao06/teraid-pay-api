import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
class TestGetWalletByUserId:
    """get_wallet_by_user_id の単体テスト。"""

    @pytest.mark.parametrize(
        ("user_id", "chain_type", "network_name", "chain_id", "expected_wallet_id"),
        [
            (101, "ETH", "sepolia", 11155111, 301),
            (101, "ETH", "mainnet", 1, None),
            (101, "ETH", "goerli", 1, None),
            (102, "ETH", "sepolia", 11155111, 304),
            (999, "ETH", "mainnet", 1, None),
        ],
    )
    def test_get_wallet_by_user_id(
        self,
        mysql_session: Session,
        user_id: int,
        chain_type: str,
        network_name: str,
        chain_id: int,
        expected_wallet_id: int | None,
    ) -> None:
        """ユーザーに紐づく chain/network 指定の wallet を取得し、未存在時は None を返すことを確認する。"""
        repository = UserRepository()

        result = repository.get_wallet_by_user_id(
            mysql_session=mysql_session,
            user_id=user_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )

        if expected_wallet_id is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet_id
        assert result.chain_type == chain_type
        assert result.network_name == network_name
        assert result.chain_id == chain_id
