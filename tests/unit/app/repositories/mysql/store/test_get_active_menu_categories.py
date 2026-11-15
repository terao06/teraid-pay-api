import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_menu_categories")
class TestGetActiveMenuCategories:
    """店舗の有効なメニューカテゴリー取得を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_menu_category_ids"),
        [
            (101, [12, 13, 11]),
            (104, []),
        ],
    )
    def test_get_active_menu_categories(
        self,
        mysql_session: Session,
        store_id: int,
        expected_menu_category_ids: list[int],
    ) -> None:
        """店舗に紐づく有効かつ未削除のカテゴリーを表示順で取得することを確認する。"""
        repository = StoreRepository()

        result = repository.get_active_menu_categories(
            mysql_session=mysql_session,
            store_id=store_id,
        )

        assert [category.menu_category_id for category in result] == (
            expected_menu_category_ids
        )
