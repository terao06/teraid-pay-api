import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_menu_categories")
class TestGetMenuCategories:
    """店舗のメニューカテゴリー検索を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_menu_category_ids"),
        [
            (101, [12, 13, 11]),
            (104, []),
        ],
    )
    def test_get_menu_categories(
        self,
        mysql_session: Session,
        store_id: int,
        expected_menu_category_ids: list[int],
    ) -> None:
        """店舗に紐づく有効かつ未削除のカテゴリーを表示順で取得することを確認する。"""
        repository = StoreRepository()

        result = repository.get_menu_categories(
            mysql_session=mysql_session,
            store_id=store_id,
            is_active=True,
            offset=0,
            limit=20,
        )

        assert [category.menu_category_id for category in result] == (
            expected_menu_category_ids
        )

    def test_filters_inactive_categories_by_name(
        self,
        mysql_session: Session,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_menu_categories(
            mysql_session=mysql_session,
            store_id=101,
            name="カテゴリー",
            is_active=False,
            offset=0,
            limit=1,
        )
        total = repository.count_menu_categories(
            mysql_session=mysql_session,
            store_id=101,
            name="カテゴリー",
            is_active=False,
        )

        assert [category.menu_category_id for category in result] == [14]
        assert total == 1

    def test_escapes_wildcards_in_name(
        self,
        mysql_session: Session,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_menu_categories(
            mysql_session=mysql_session,
            store_id=101,
            name="%",
            is_active=True,
        )

        assert result == []
