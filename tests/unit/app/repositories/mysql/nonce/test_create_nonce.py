from datetime import datetime

from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.repositories.mysql.nonce_repository import NonceRepository


class TestCreateNonce:
    """create_nonce の動作を検証する。"""

    def test_create_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = NonceRepository()
        nonce = Nonce(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            nonce="test-store-wallet-nonce",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        saved_nonce = repository.create_nonce(mysql_session, nonce)
        mysql_session.flush()

        assert saved_nonce.nonce_id is not None
        assert saved_nonce.wallet_address == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert saved_nonce.chain_type == "ethereum"
        assert saved_nonce.network_name == "sepolia"
        assert saved_nonce.nonce == "test-store-wallet-nonce"
        assert saved_nonce.expires_at == datetime(2026, 4, 13, 12, 0, 0)
        assert saved_nonce.used_at is None
