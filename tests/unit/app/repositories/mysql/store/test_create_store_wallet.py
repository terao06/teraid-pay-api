from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet
from app.repositories.mysql.store_repository import StoreRepository
from app.repositories.mysql.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestCreateStoreWallet:
    """create_store_wallet の動作を検証する。"""

    def test_create_store_wallet(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = StoreRepository()
        new_wallet = Wallet(
            wallet_address="0xcccccccccccccccccccccccccccccccccccccccc",
            chain_type="ethereum",
            network_name="sepolia",
            token_symbol="JPYC",
            chain_id=11155111,
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )
        saved_wallet = WalletRepository().create_wallet(mysql_session, new_wallet)

        store_wallet = StoreWallet(
            store_id=101,
            wallet_id=saved_wallet.wallet_id,
        )

        repository.create_store_wallet(mysql_session, store_wallet)
        mysql_session.flush()

        saved_store_wallet = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == saved_wallet.wallet_id)
            .one()
        )

        assert saved_store_wallet.store_wallet_id is not None
        assert saved_store_wallet.store_id == 101
        assert saved_store_wallet.wallet_id == saved_wallet.wallet_id
        assert saved_store_wallet.created_at is not None
        assert saved_store_wallet.updated_at is not None
        assert saved_store_wallet.deleted_at is None
