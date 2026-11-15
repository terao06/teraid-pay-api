"""メニュー詳細取得Repositoryのテスト。"""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.repositories.mysql.store_menu_repository import StoreMenuRepository


@pytest.mark.usefixtures("insert_menu_items")
class TestGetMenuDetail:
    """StoreMenuRepositoryのメニュー詳細取得を検証する。"""

    def test_get_menu_detail_with_ordered_options(
        self,
        mysql_session: Session,
    ) -> None:
        """非公開状態も含む未削除オプションを表示順で取得する。"""
        first_group = MenuOptionGroup(
            menu_option_group_id=31,
            menu_item_id=21,
            name="トッピング",
            min_selections=0,
            max_selections=2,
            display_order=2,
            is_active=False,
        )
        second_group = MenuOptionGroup(
            menu_option_group_id=32,
            menu_item_id=21,
            name="サイズ",
            min_selections=1,
            max_selections=1,
            display_order=1,
            is_active=True,
        )
        mysql_session.add_all([first_group, second_group])
        mysql_session.flush()
        mysql_session.add_all(
            [
                MenuOption(
                    menu_option_id=41,
                    menu_option_group_id=32,
                    name="通常",
                    additional_price=0,
                    display_order=1,
                    is_available=True,
                ),
                MenuOption(
                    menu_option_id=42,
                    menu_option_group_id=32,
                    name="大盛り",
                    additional_price=100,
                    display_order=2,
                    is_available=False,
                ),
                MenuOption(
                    menu_option_id=43,
                    menu_option_group_id=32,
                    name="削除済み",
                    additional_price=200,
                    display_order=0,
                    is_available=True,
                    deleted_at=datetime(2026, 2, 1),
                ),
            ]
        )
        mysql_session.flush()

        rows = StoreMenuRepository().get_menu_detail(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=21,
        )

        assert [row[0].menu_item_id for row in rows] == [21, 21, 21]
        assert [row[1] for row in rows] == ["フード", "フード", "フード"]
        assert [row[2].menu_option_group_id for row in rows] == [32, 32, 31]
        assert [
            row[3].menu_option_id if row[3] is not None else None for row in rows
        ] == [41, 42, None]

    def test_get_menu_detail_returns_null_category_for_deleted_category(
        self,
        mysql_session: Session,
    ) -> None:
        """削除済みカテゴリーの商品をカテゴリーなしとして取得する。"""
        rows = StoreMenuRepository().get_menu_detail(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=23,
        )

        assert len(rows) == 1
        assert rows[0][0].menu_item_id == 23
        assert rows[0][1] is None
        assert rows[0][2] is None
        assert rows[0][3] is None

    @pytest.mark.parametrize("menu_item_id", [25, 26, 999])
    def test_get_menu_detail_returns_empty_for_inaccessible_item(
        self,
        mysql_session: Session,
        menu_item_id: int,
    ) -> None:
        """削除済み、別店舗、未存在の商品を取得しない。"""
        rows = StoreMenuRepository().get_menu_detail(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=menu_item_id,
        )

        assert rows == []
