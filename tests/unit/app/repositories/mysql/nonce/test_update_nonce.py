from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.repositories.mysql.nonce_repository import NonceRepository

@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestUpdateNonce:
    """update_nonce の動作を検証する。"""

    def test_update_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = NonceRepository()
        nonce = (
            mysql_session.query(Nonce)
            .filter(Nonce.nonce_id == 2)
            .one()
        )
        used_at = datetime(2026, 4, 13, 11, 30, 0)

        nonce.used_at = used_at
        repository.update_nonce(mysql_session, nonce)
        mysql_session.flush()
        mysql_session.expire_all()

        saved_nonce = (
            mysql_session.query(Nonce)
            .filter(Nonce.nonce_id == 2)
            .one()
        )

        assert saved_nonce.nonce_id == 2
        assert saved_nonce.nonce == "available-latest"
        assert saved_nonce.used_at == used_at
