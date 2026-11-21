"""実 MySQL で注文の絞り込み、ページ抽出および JOIN を検証する。"""

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.mysql.menu_order import OrderFulfillmentStatus
from app.repositories.mysql.store_order_repository import StoreOrderRepository


@pytest.mark.usefixtures("insert_order_list_data")
class TestGetOrders:
    """オーダー一覧リポジトリを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(
        ("store_id", "fulfillment_status", "offset", "expected_ids", "total"),
        [
            (111, OrderFulfillmentStatus.UNSERVED, 0, [870101, 870102], 3),
            (111, OrderFulfillmentStatus.UNSERVED, 2, [870103], 3),
            (111, OrderFulfillmentStatus.UNSERVED, 10, [], 3),
            (111, OrderFulfillmentStatus.SERVED, 0, [870109, 870108], 3),
            (111, OrderFulfillmentStatus.SERVED, 2, [870104], 3),
            (112, OrderFulfillmentStatus.UNSERVED, 0, [870107], 1),
            (112, OrderFulfillmentStatus.SERVED, 0, [870111], 1),
            (104, OrderFulfillmentStatus.SERVED, 0, [], 0),
        ],
    )
    def test_filters_and_paginates_by_order(
        self,
        mysql_session: Session,
        store_id: int,
        fulfillment_status: OrderFulfillmentStatus,
        offset: int,
        expected_ids: list[int],
        total: int,
    ) -> None:
        """店舗・提供状態で絞り込み、注文単位のページ抽出と総数を検証する。

        Args:
            mysql_session: 実 DB のセッション。
            store_id: 検索対象の店舗 ID。
            fulfillment_status: 取得対象の提供状態。
            offset: ページの開始位置。
            expected_ids: 期待する順の注文 ID。
            total: ページ送り前の総件数。

        Returns:
            なし。
        """
        rows, count = StoreOrderRepository().get_orders(mysql_session, store_id, fulfillment_status, offset, limit=2)

        assert list(dict.fromkeys(row["menu_order_id"] for row in rows)) == expected_ids
        assert count == total

    @pytest.mark.parametrize(("offset", "expected_query_count"), [(0, 2), (3, 1)])
    def test_loads_page_with_one_joined_query(
        self, mysql_session: Session, offset: int, expected_query_count: int
    ) -> None:
        """集計とページ取得の SQL 数を測り、ページ抽出後の結合を検証する。

        Args:
            mysql_session: 実 DB のセッション。
            offset: ページの開始位置。
            expected_query_count: 発行される SQL 数。

        Returns:
            なし。
        """
        statements: list[str] = []
        connection = mysql_session.connection()

        def record_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
            """リポジトリが発行した SQL を記録する。"""
            statements.append(statement)

        event.listen(connection, "before_cursor_execute", record_statement)
        try:
            rows, total = StoreOrderRepository().get_orders(
                mysql_session, 111, OrderFulfillmentStatus.UNSERVED, offset, limit=1
            )
        finally:
            event.remove(connection, "before_cursor_execute", record_statement)

        assert total == 3
        assert len(statements) == expected_query_count
        if offset >= total:
            assert rows == []
            return

        assert statements[1].upper().count("LEFT OUTER JOIN") == 4
        assert {row["menu_order_id"] for row in rows} == {870101}
        assert {row["device_name"] for row in rows} == {"カテゴリー別メニュー取得端末"}
        assert [row["menu_item_name"] for row in rows] == ["特製チーズバーガー", "特製チーズバーガー", "フライドポテト"]
        assert [row["option_name"] for row in rows] == ["追加ベーコン", "追加チーズ", None]
