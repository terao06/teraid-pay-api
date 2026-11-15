import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetStoreById:
    """get_store_by_id の動作を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_store_id"),
        [
            (101, 101),
            (102, 102),
            (103, None),
            (999, None),
        ],
    )
    def test_get_store_by_id(
        self,
        mysql_session: Session,
        store_id: int,
        expected_store_id: int | None,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = StoreRepository()

        result = repository.get_store_by_id(mysql_session, store_id)

        if expected_store_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_id == expected_store_id
