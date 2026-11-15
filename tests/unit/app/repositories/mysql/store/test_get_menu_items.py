import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_item import MenuItem
from app.repositories.mysql.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_menu_items")
class TestGetMenuItems:
    """店舗のメニュー商品一覧取得を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_menu_items"),
        [
            (
                101,
                [
                    (21, "フード"),
                    (22, "ドリンク"),
                    (23, None),
                    (24, None),
                ],
            ),
            (104, []),
        ],
    )
    def test_get_menu_items(
        self,
        mysql_session: Session,
        store_id: int,
        expected_menu_items: list[tuple[int, str | None]],
    ) -> None:
        """店舗の未削除商品と未削除カテゴリー名を表示順で取得することを確認する。"""
        result = StoreRepository().get_menu_items(
            mysql_session=mysql_session,
            store_id=store_id,
        )

        actual_menu_items = [
            (menu_item.menu_item_id, menu_category_name)
            for menu_item, menu_category_name in result
        ]
        if store_id == 104:
            assert actual_menu_items == expected_menu_items
            return

        fixture_menu_items = [
            menu_item
            for menu_item in actual_menu_items
            if menu_item[0] in {21, 22, 23, 24}
        ]
        assert fixture_menu_items == expected_menu_items
        assert 25 not in [menu_item[0] for menu_item in actual_menu_items]
        assert 26 not in [menu_item[0] for menu_item in actual_menu_items]

    @pytest.mark.parametrize(
        ("filters", "expected_ids"),
        [
            ({"menu_category_id": 12}, [21]),
            ({"is_available": False}, [22]),
            (
                {
                    "menu_category_id": 12,
                    "is_available": True,
                },
                [21],
            ),
        ],
    )
    def test_get_menu_items_with_filters(
        self,
        mysql_session: Session,
        filters: dict[str, object],
        expected_ids: list[int],
    ) -> None:
        """商品名・カテゴリー・公開状態を組み合わせて検索できることを確認する。"""
        result = StoreRepository().get_menu_items(
            mysql_session=mysql_session,
            store_id=101,
            **filters,
        )

        assert [menu_item.menu_item_id for menu_item, _ in result] == expected_ids

    def test_get_menu_items_with_partial_name(
        self,
        mysql_session: Session,
    ) -> None:
        """商品名の一部を指定して検索できることを確認する。"""
        menu_name = (
            mysql_session.query(MenuItem.name)
            .filter(MenuItem.menu_item_id == 22)
            .scalar()
        )
        assert menu_name is not None

        result = StoreRepository().get_menu_items(
            mysql_session=mysql_session,
            store_id=101,
            name=menu_name,
        )

        assert [menu_item.menu_item_id for menu_item, _ in result] == [22]
