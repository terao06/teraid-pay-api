"""メニューカテゴリー詳細取得Repositoryのテスト。"""

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_menu_category_repository import (
    StoreMenuCategoryRepository,
)


@pytest.mark.usefixtures("insert_menu_categories")
class TestGetMenuCategory:
    """店舗の未削除メニューカテゴリー詳細取得を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "menu_category_id", "expected_menu_category_id"),
        [
            (101, 12, 12),
            (101, 14, 14),
            (101, 15, None),
            (101, 16, None),
            (102, 16, 16),
        ],
    )
    def test_get_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
        expected_menu_category_id: int | None,
    ) -> None:
        """店舗、ID、削除状態に一致するカテゴリーだけを取得する。"""
        result = StoreMenuCategoryRepository().get_menu_category(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
        )

        if expected_menu_category_id is None:
            assert result is None
            return

        assert result is not None
        assert result.menu_category_id == expected_menu_category_id
