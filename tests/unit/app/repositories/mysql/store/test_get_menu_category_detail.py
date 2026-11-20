"""メニューカテゴリー詳細取得Repositoryのテスト。"""

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.mysql.menu_category import MenuCategory
from app.repositories.mysql.store_menu_category_repository import (
    StoreMenuCategoryRepository,
)


@pytest.mark.usefixtures("insert_menu_categories")
class TestGetMenuCategoryDetail:
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
    def test_get_menu_category_detail(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
        expected_menu_category_id: int | None,
    ) -> None:
        """店舗、ID、削除状態に一致するカテゴリーだけを取得する。"""
        result = StoreMenuCategoryRepository().get_menu_category_detail(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
        )

        if expected_menu_category_id is None:
            assert result is None
            return

        assert result is not None
        assert result.menu_category_id == expected_menu_category_id


@pytest.mark.usefixtures("insert_menu_category_deletion_data")
def test_locks_category_until_transaction_ends(mysql_engine: Engine) -> None:
    """排他ロックが別セッションのロック取得をトランザクション終了まで防ぐ。

    Args:
        mysql_engine: 独立した2つのセッションに接続を提供するMySQL Engine。

    Returns:
        なし。
    """
    menu_category_id = 830006
    competing_query = (
        select(MenuCategory.menu_category_id)
        .where(MenuCategory.menu_category_id == menu_category_id)
        .with_for_update(nowait=True)
    )
    with Session(mysql_engine) as locking_session, Session(mysql_engine) as competing_session:
        category = StoreMenuCategoryRepository().get_menu_category_detail(
            mysql_session=locking_session,
            store_id=107,
            menu_category_id=menu_category_id,
            lock_for_update=True,
        )
        assert category is not None
        assert category.menu_category_id == menu_category_id

        with pytest.raises(OperationalError) as exc_info:
            competing_session.scalar(competing_query)
        # MySQLのER_LOCK_NOWAIT。
        assert exc_info.value.orig.args[0] == 3572

        competing_session.rollback()
        locking_session.rollback()
        assert competing_session.scalar(competing_query) == menu_category_id
