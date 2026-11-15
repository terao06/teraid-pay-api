"""メニュー基本情報更新Repositoryのテスト。"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_menu_repository import StoreMenuRepository


@pytest.mark.usefixtures("insert_menu_items")
class TestUpdateMenu:
    """StoreMenuRepositoryの商品取得と保存を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "menu_item_id", "expected_id"),
        [
            (101, 21, 21),
            (101, 22, 22),
            (101, 25, None),
            (101, 26, None),
            (101, 999, None),
        ],
    )
    def test_get_menu_item(
        self,
        mysql_session: Session,
        store_id: int,
        menu_item_id: int,
        expected_id: int | None,
    ) -> None:
        """店舗境界と論理削除条件に一致する商品だけを取得する。"""
        item = StoreMenuRepository().get_menu_item(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_item_id=menu_item_id,
            lock_for_update=True,
        )

        assert (item.menu_item_id if item is not None else None) == expected_id

    def test_save_menu_item(self, mysql_session: Session) -> None:
        """変更した商品基本情報をセッションへ反映する。"""
        repository = StoreMenuRepository()
        item = repository.get_menu_item(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=21,
            lock_for_update=True,
        )
        assert item is not None
        item.name = "Repository更新商品"
        item.price = Decimal("975.000000")

        updated_item = repository.save_menu_item(
            mysql_session=mysql_session,
            menu_item=item,
        )

        assert updated_item.name == "Repository更新商品"
        assert updated_item.price == Decimal("975.000000")
