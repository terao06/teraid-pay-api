"""会計候補の注文、明細、オプションを一度に取得する検索を検証する。"""

import pytest
from sqlalchemy import event

from app.repositories.mysql.device_order_repository import DeviceOrderRepository


@pytest.mark.usefixtures("insert_device_checkout_data")
class TestGetCheckoutOrders:
    """一括会計の検索条件と結合結果を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_reads_unpaid_orders_and_details_in_one_select(self, mysql_session) -> None:
        """未払い注文の保存済み明細を1回のSELECTで取得する。

        Args:
            mysql_session: 初期化済みのテスト用MySQLセッション。

        Returns:
            なし。
        """
        statements = []

        def _record_statement(conn, cursor, statement, parameters, context, executemany):
            """発行したSQLを確認用に記録する。"""
            statements.append(statement)

        connection = mysql_session.connection()
        event.listen(connection, "before_cursor_execute", _record_statement)
        try:
            rows = DeviceOrderRepository().get_checkout_orders(mysql_session, 9101, 902001)
        finally:
            event.remove(connection, "before_cursor_execute", _record_statement)

        assert len(statements) == 1
        assert statements[0].upper().count("LEFT OUTER JOIN") == 2
        detail_ids = [
            (order.menu_order_id, item.menu_order_item_id, option.menu_order_item_option_id if option else None)
            for order, item, option in rows
        ]
        assert detail_ids == [
            (903001, 907001, 908001),
            (903001, 907001, 908002),
            (903002, 907002, None),
        ]
