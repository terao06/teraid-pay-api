from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_nonces", "insert_user_nonces")
class TestGetLatestAvailableNonce:
    """get_latest_available_nonce の単体テスト。"""

    def test_get_latest_available_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        """条件に一致する未使用かつ有効期限内の最新 nonce を返すことを検証する。"""
        repository = UserRepository()

        result = repository.get_latest_available_nonce(
            mysql_session=mysql_session,
            user_id=101,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert result is not None
        assert result.nonce_id == 2
        assert result.nonce == "available-latest"
        assert result.used_at is None
        assert result.expires_at == datetime(2026, 4, 13, 12, 5, 0)

    def test_get_latest_available_nonce_returns_none(
        self,
        mysql_session: Session,
    ) -> None:
        """一致する user_nonce が存在しない場合は None を返すことを検証する。"""
        repository = UserRepository()

        result = repository.get_latest_available_nonce(
            mysql_session=mysql_session,
            user_id=102,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert result is None
