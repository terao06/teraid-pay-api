"""メニュー削除で再利用するRepositoryの検索とフラッシュを検証する。"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.repositories.mysql.store_menu_repository import StoreMenuRepository


@pytest.mark.usefixtures("insert_menu_deletion_data")
def test_flushes_menu_and_child_deletion_timestamps_before_commit(mysql_session: Session) -> None:
    """排他ロックで取得した未削除行への変更をコミット前にMySQLへ反映する。

    Args:
        mysql_session: 自動フラッシュを無効にしたテスト用MySQLセッション。

    Returns:
        なし。
    """
    repository = StoreMenuRepository()
    with mysql_session.begin():
        item = repository.get_menu_item(
            mysql_session=mysql_session, store_id=101, menu_item_id=840001, lock_for_update=True
        )
        assert item is not None
        groups = repository.get_menu_option_groups(
            mysql_session=mysql_session, menu_item_id=item.menu_item_id, lock_for_update=True
        )
        assert [group.menu_option_group_id for group in groups] == [840001]
        options = repository.get_menu_options(
            mysql_session=mysql_session, menu_option_group_ids=[840001], lock_for_update=True
        )
        assert [option.menu_option_id for option in options] == [840001]

        repository.soft_delete_menu_option(mysql_session=mysql_session, menu_option=options[0])
        assert mysql_session.scalar(
            select(MenuOption.deleted_at).where(MenuOption.menu_option_id == 840001)
        ) is not None

        repository.soft_delete_menu_option_group(mysql_session=mysql_session, menu_option_group=groups[0])
        assert mysql_session.scalar(
            select(MenuOptionGroup.deleted_at).where(MenuOptionGroup.menu_option_group_id == 840001)
        ) is not None

        repository.soft_delete_menu_item(mysql_session=mysql_session, menu_item=item)
        assert mysql_session.scalar(
            select(MenuItem.deleted_at).where(MenuItem.menu_item_id == 840001)
        ) is not None
