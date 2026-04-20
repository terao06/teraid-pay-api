from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet
from app.repositories.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestCreateWallet:
    def test_create_wallet(
        self,
        session: Session,
    ) -> None:
        repository = WalletRepository()
        wallet = Wallet(
            wallet_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            chain_type="ethereum",
            network_name="sepolia",
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        saved_wallet = repository.create_wallet(session, wallet)
        session.flush()

        assert saved_wallet.wallet_id is not None
        assert saved_wallet.wallet_address == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        assert saved_wallet.chain_type == "ethereum"
        assert saved_wallet.network_name == "sepolia"
        assert saved_wallet.is_active is True
        assert saved_wallet.verified_at == datetime(2026, 4, 13, 12, 0, 0)