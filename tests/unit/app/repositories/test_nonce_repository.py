from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.repositories.nonce_repository import NonceRepository


class TestCreateNonce:
    def test_create_nonce(
        self,
        session: Session,
    ) -> None:
        repository = NonceRepository()
        nonce = Nonce(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            nonce="test-store-wallet-nonce",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        saved_nonce = repository.create_nonce(session, nonce)
        session.flush()

        assert saved_nonce.nonce_id is not None
        assert saved_nonce.wallet_address == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert saved_nonce.chain_type == "ethereum"
        assert saved_nonce.network_name == "sepolia"
        assert saved_nonce.nonce == "test-store-wallet-nonce"
        assert saved_nonce.expires_at == datetime(2026, 4, 13, 12, 0, 0)
        assert saved_nonce.used_at is None


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestUpdateNonce:
    def test_update_nonce(
        self,
        session: Session,
    ) -> None:
        repository = NonceRepository()
        nonce = (
            session.query(Nonce)
            .filter(Nonce.nonce_id == 2)
            .one()
        )
        used_at = datetime(2026, 4, 13, 11, 30, 0)

        nonce.used_at = used_at
        repository.update_nonce(session, nonce)
        session.flush()
        session.expire_all()

        saved_nonce = (
            session.query(Nonce)
            .filter(Nonce.nonce_id == 2)
            .one()
        )

        assert saved_nonce.nonce_id == 2
        assert saved_nonce.nonce == "available-latest"
        assert saved_nonce.used_at == used_at
