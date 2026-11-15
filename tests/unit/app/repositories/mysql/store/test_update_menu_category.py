"""メニューカテゴリー更新Repositoryのテスト。"""

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_category import MenuCategory
from app.repositories.mysql.store_menu_category_repository import (
    StoreMenuCategoryRepository,
)


@pytest.mark.usefixtures("insert_menu_categories")
class TestUpdateMenuCategory:
    """メニューカテゴリーの永続化を検証する。"""

    def test_update_menu_category(self, mysql_session: Session) -> None:
        """変更したカテゴリー情報をセッションへ反映する。"""
        category = (
            mysql_session.query(MenuCategory)
            .filter(MenuCategory.menu_category_id == 14)
            .one()
        )
        category.name = "更新カテゴリー"
        category.display_order = 3
        category.is_active = True

        result = StoreMenuCategoryRepository().update_menu_category(
            mysql_session=mysql_session,
            menu_category=category,
        )

        assert result.menu_category_id == 14
        assert result.name == "更新カテゴリー"
        assert result.display_order == 3
        assert result.is_active is True
