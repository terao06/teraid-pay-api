import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
class TestGetUserWallet:
    """get_user_wallet の単体テスト。"""

    @pytest.mark.parametrize(
        ("user_id", "expected_wallet"),
        [
            (
                101,
                {
                    "wallet_id": 301,
                    "wallet_address": "0x1111111111111111111111111111111111111111",
                    "chain_type": "ETH",
                    "network_name": "sepolia",
                    "is_active": True,
                    "verified_at": "2024-01-10 12:00:00",
                },
            ),
            (
                999,
                None,
            ),
            (
                103,
                None,
            ),
        ],
    )
    def test_get_user_wallet(
        self,
        mysql_session: Session,
        user_id: int,
        expected_wallet: dict | None,
    ) -> None:
        """ユーザーに紐づくウォレットを取得し、未存在時は None を返すことを確認する。"""
        repository = UserRepository()

        result = repository.get_user_wallet(mysql_session, user_id)

        if expected_wallet is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet["wallet_id"]
        assert result.wallet_address == expected_wallet["wallet_address"]
        assert result.chain_type == expected_wallet["chain_type"]
        assert result.network_name == expected_wallet["network_name"]
        assert result.is_active == expected_wallet["is_active"]
        verified_at = result.verified_at.isoformat(sep=" ") if result.verified_at else None
        assert verified_at == expected_wallet["verified_at"]
