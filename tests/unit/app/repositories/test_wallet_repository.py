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
            token_symbol="JPYC",
            chain_id=11155111,
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        saved_wallet = repository.create_wallet(session, wallet)
        session.flush()

        assert saved_wallet.wallet_id is not None
        assert saved_wallet.wallet_address == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        assert saved_wallet.chain_type == "ethereum"
        assert saved_wallet.network_name == "sepolia"
        assert saved_wallet.token_symbol == "JPYC"
        assert saved_wallet.chain_id == 11155111
        assert saved_wallet.is_active is True
        assert saved_wallet.verified_at == datetime(2026, 4, 13, 12, 0, 0)


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestDeleteWallet:
    def test_delete_wallet_by_wallet_id(
        self,
        session: Session,
    ) -> None:
        repository = WalletRepository()
        wallet_id = 301

        before = session.query(Wallet).where(Wallet.wallet_id == wallet_id).one()
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_wallet_by_wallet_id(session, wallet_id)
        session.flush()
        session.expire_all()

        after = session.query(Wallet).where(Wallet.wallet_id == wallet_id).one()
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at
