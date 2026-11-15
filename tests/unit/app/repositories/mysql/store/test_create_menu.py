from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_option import MenuOption
from app.repositories.mysql.store_menu_repository import StoreMenuRepository


@pytest.mark.usefixtures("insert_stores", "insert_menu_categories")
class TestCreateMenu:
    """メニュー商品、オプショングループ、オプションの登録を検証する。"""

    def test_create_menu(
        self,
        mysql_session: Session,
    ) -> None:
        """商品、オプショングループ、オプションへIDを付与して保存することを確認する。"""
        repository = StoreMenuRepository()
        menu_item = MenuItem(
            store_id=101,
            menu_category_id=12,
            name="リポジトリテスト商品",
            description="商品説明",
            price=Decimal("800.000000"),
            token_symbol="JPYC",
            image_extension="jpg",
            is_available=True,
            display_order=1,
        )

        saved_menu_item = repository.create_menu_item(
            mysql_session=mysql_session,
            menu_item=menu_item,
        )
        saved_menu_option_group = repository.create_menu_option_group(
            mysql_session=mysql_session,
            menu_option_group=MenuOptionGroup(
                menu_item_id=saved_menu_item.menu_item_id,
                name="サイズ",
                min_selections=1,
                max_selections=1,
                display_order=1,
                is_active=True,
            ),
        )
        saved_menu_option = repository.create_menu_option(
            mysql_session=mysql_session,
            menu_option=MenuOption(
                menu_option_group_id=(
                    saved_menu_option_group.menu_option_group_id
                ),
                name="大盛り",
                additional_price=Decimal("100.000000"),
                display_order=1,
                is_available=True,
            ),
        )

        stored_menu_item = (
            mysql_session.query(MenuItem)
            .filter(MenuItem.menu_item_id == saved_menu_item.menu_item_id)
            .one()
        )
        stored_menu_option_group = (
            mysql_session.query(MenuOptionGroup)
            .filter(
                MenuOptionGroup.menu_option_group_id
                == saved_menu_option_group.menu_option_group_id
            )
            .one()
        )
        stored_menu_option = (
            mysql_session.query(MenuOption)
            .filter(MenuOption.menu_option_id == saved_menu_option.menu_option_id)
            .one()
        )

        assert stored_menu_item.store_id == 101
        assert stored_menu_item.menu_category_id == 12
        assert stored_menu_item.price == Decimal("800.000000")
        assert stored_menu_item.image_extension == "jpg"
        assert stored_menu_option_group.menu_item_id == stored_menu_item.menu_item_id
        assert stored_menu_option_group.min_selections == 1
        assert stored_menu_option_group.max_selections == 1
        assert (
            stored_menu_option.menu_option_group_id
            == stored_menu_option_group.menu_option_group_id
        )
        assert stored_menu_option.additional_price == Decimal("100.000000")
