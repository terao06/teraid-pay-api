from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet
from app.repositories.mysql.wallet_repository import WalletRepository

@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestCreateWallet:
    """create_wallet の動作を検証する。"""

    def test_create_wallet(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = WalletRepository()
        wallet = Wallet(
            wallet_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            chain_type="ethereum",
            network_name="sepolia",
            token_symbol="JPYC",
            chain_id=11155111,
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        saved_wallet = repository.create_wallet(mysql_session, wallet)
        mysql_session.flush()

        assert saved_wallet.wallet_id is not None
        assert saved_wallet.wallet_address == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        assert saved_wallet.chain_type == "ethereum"
        assert saved_wallet.network_name == "sepolia"
        assert saved_wallet.token_symbol == "JPYC"
        assert saved_wallet.chain_id == 11155111
        assert saved_wallet.is_active is True
        assert saved_wallet.is_permitted is True
        assert saved_wallet.verified_at == datetime(2026, 4, 13, 12, 0, 0)
