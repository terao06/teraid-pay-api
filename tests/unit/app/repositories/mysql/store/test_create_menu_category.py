import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_category import MenuCategory
from app.repositories.mysql.store_menu_category_repository import StoreMenuCategoryRepository


@pytest.mark.usefixtures("insert_stores")
class TestCreateMenuCategory:
    def test_create_menu_category(self, mysql_session: Session) -> None:
        menu_category = MenuCategory(
            store_id=101,
            name="カテゴリー登録リポジトリテスト",
            image_extension="png",
            display_order=3,
            is_active=True,
        )

        saved = StoreMenuCategoryRepository().create_menu_category(
            mysql_session=mysql_session,
            menu_category=menu_category,
        )

        stored = (
            mysql_session.query(MenuCategory)
            .filter(MenuCategory.menu_category_id == saved.menu_category_id)
            .one()
        )
        assert stored.store_id == 101
        assert stored.name == "カテゴリー登録リポジトリテスト"
        assert stored.image_extension == "png"
        assert stored.display_order == 3
        assert stored.is_active is True
