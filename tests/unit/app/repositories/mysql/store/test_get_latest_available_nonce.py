from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_nonce_repository import StoreNonceRepository


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestGetLatestAvailableNonce:
    """get_latest_available_nonce の動作を検証する。"""

    def test_get_latest_available_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = StoreNonceRepository()
        base_expires_at = datetime(2026, 4, 13, 12, 0, 0)

        result = repository.get_latest_available_nonce(
            mysql_session=mysql_session,
            store_id=101,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=base_expires_at,
        )

        assert result is not None
        assert result.nonce == "available-latest"
        assert result.used_at is None
        assert result.expires_at == datetime(2026, 4, 13, 12, 5, 0)

    def test_get_latest_available_nonce_returns_none(
        self,
        mysql_session: Session,
    ) -> None:
        """対象が存在しない場合の戻り値を検証する。"""
        repository = StoreNonceRepository()

        result = repository.get_latest_available_nonce(
            mysql_session=mysql_session,
            store_id=102,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert result is None
