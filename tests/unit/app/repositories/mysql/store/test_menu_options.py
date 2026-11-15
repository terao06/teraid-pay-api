"""メニューオプションRepositoryのテスト。"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.repositories.mysql.store_menu_repository import StoreMenuRepository


@pytest.mark.usefixtures("insert_menu_items")
class TestMenuOptions:
    """オプショングループとオプションの汎用取得・保存・削除を検証する。"""

    def test_save_get_and_soft_delete(
        self,
        mysql_session: Session,
    ) -> None:
        """保存した構成を取得でき、論理削除後は取得対象外になる。"""
        repository = StoreMenuRepository()
        group = repository.save_menu_option_group(
            mysql_session=mysql_session,
            menu_option_group=MenuOptionGroup(
                menu_item_id=21,
                name="Repositoryサイズ",
                min_selections=1,
                max_selections=1,
                display_order=1,
                is_active=True,
            ),
        )
        option = repository.save_menu_option(
            mysql_session=mysql_session,
            menu_option=MenuOption(
                menu_option_group_id=group.menu_option_group_id,
                name="Repository通常",
                additional_price=Decimal("0.000000"),
                display_order=1,
                is_available=True,
            ),
        )

        groups = repository.get_menu_option_groups(
            mysql_session=mysql_session,
            menu_item_id=21,
            lock_for_update=True,
        )
        options = repository.get_menu_options(
            mysql_session=mysql_session,
            menu_option_group_ids=[group.menu_option_group_id],
            lock_for_update=True,
        )

        assert group.menu_option_group_id in {
            stored_group.menu_option_group_id for stored_group in groups
        }
        assert [stored_option.menu_option_id for stored_option in options] == [
            option.menu_option_id
        ]

        repository.soft_delete_menu_option(
            mysql_session=mysql_session,
            menu_option=option,
        )
        repository.soft_delete_menu_option_group(
            mysql_session=mysql_session,
            menu_option_group=group,
        )

        remaining_group_ids = {
            stored_group.menu_option_group_id
            for stored_group in repository.get_menu_option_groups(
                mysql_session=mysql_session,
                menu_item_id=21,
            )
        }
        assert group.menu_option_group_id not in remaining_group_ids
        assert repository.get_menu_options(
            mysql_session=mysql_session,
            menu_option_group_ids=[group.menu_option_group_id],
        ) == []

    def test_get_menu_options_with_empty_group_ids(
        self,
        mysql_session: Session,
    ) -> None:
        """グループIDが空の場合はクエリせず空配列を返す。"""
        assert StoreMenuRepository().get_menu_options(
            mysql_session=mysql_session,
            menu_option_group_ids=[],
        ) == []
