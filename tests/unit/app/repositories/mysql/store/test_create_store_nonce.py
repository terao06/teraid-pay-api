from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.store_nonce import StoreNonce
from app.repositories.mysql.nonce_repository import NonceRepository
from app.repositories.mysql.store_nonce_repository import StoreNonceRepository


@pytest.mark.usefixtures("insert_stores")
class TestCreateStoreNonce:
    """create_store_nonce の動作を検証する。"""

    def test_create_store_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = StoreNonceRepository()
        nonce = Nonce(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            nonce="test-store-wallet-nonce",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )
        saved_nonce = NonceRepository().create_nonce(mysql_session, nonce)

        store_nonce = StoreNonce(store_id=101, nonce_id=saved_nonce.nonce_id)
        repository.create_store_nonce(mysql_session, store_nonce)
        mysql_session.flush()

        saved_store_nonce = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.store_id == 101, StoreNonce.nonce_id == saved_nonce.nonce_id)
            .one()
        )

        assert saved_store_nonce.store_nonce_id is not None
        assert saved_store_nonce.store_id == 101
        assert saved_store_nonce.nonce_id == saved_nonce.nonce_id
        assert saved_store_nonce.created_at is not None
        assert saved_store_nonce.updated_at is not None
        assert saved_store_nonce.deleted_at is None
