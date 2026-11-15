import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_wallet_repository import StoreWalletRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetStoreWallet:
    """get_store_wallet の動作を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_wallet"),
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
        ],
    )
    def test_get_store_wallet(
        self,
        mysql_session: Session,
        store_id: int | None,
        expected_wallet: dict,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = StoreWalletRepository()

        result = repository.get_store_wallet(mysql_session, store_id)

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
