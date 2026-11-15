import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_repository import StoreRepository

@pytest.mark.usefixtures("insert_stores", "insert_store_managers")
class TestGetStoreManagerById:
    """店舗管理者IDによるJOIN検索を検証する。"""

    @pytest.mark.parametrize(
        ("store_manager_id", "expected_store_manager_id"),
        [
            (201, 201),
            (202, 202),
            (203, None),
            (204, None),
            (999, None),
        ],
    )
    def test_get_store_manager_by_id(
        self,
        mysql_session: Session,
        store_manager_id: int,
        expected_store_manager_id: int | None,
    ) -> None:
        """管理者と所属店舗が未削除の場合のみ管理者IDで取得できることを検証する。"""
        result = StoreRepository().get_store_manager_by_id(
            mysql_session=mysql_session,
            store_manager_id=store_manager_id,
        )

        if expected_store_manager_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_manager_id == expected_store_manager_id
