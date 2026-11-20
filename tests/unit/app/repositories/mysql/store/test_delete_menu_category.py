"""メニューカテゴリー削除Repositoryのテスト。"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mysql.menu_category import MenuCategory
from app.repositories.mysql.store_menu_category_repository import StoreMenuCategoryRepository


@pytest.mark.usefixtures("insert_menu_category_deletion_data")
def test_flushes_deletion_timestamp_before_commit(mysql_session: Session) -> None:
    """論理削除がコミット前に削除日時を実DBへ反映する。

    Args:
        mysql_session: 自動フラッシュを無効にしたテスト用MySQLセッション。

    Returns:
        なし。
    """
    menu_category_id = 830005
    repository = StoreMenuCategoryRepository()

    with mysql_session.begin():
        category = repository.get_menu_category_detail(
            mysql_session=mysql_session,
            store_id=107,
            menu_category_id=menu_category_id,
            lock_for_update=True,
        )
        assert category is not None
        assert category.deleted_at is None

        repository.soft_delete_menu_category(mysql_session=mysql_session, menu_category=category)

        saved_deleted_at = mysql_session.execute(
            select(MenuCategory.deleted_at).where(MenuCategory.menu_category_id == menu_category_id)
        ).scalar_one()
        assert saved_deleted_at is not None
