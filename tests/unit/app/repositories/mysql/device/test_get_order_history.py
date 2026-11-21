"""MySQLの注文履歴クエリを検証する。"""

import pytest
from sqlalchemy import event

from app.repositories.mysql.device_order_repository import DeviceOrderRepository


ACTIVE_DEVICE = "89100100-0000-4000-8000-000000891001"
CHECKOUT_DEVICE = "89100200-0000-4000-8000-000000891002"


@pytest.mark.usefixtures("insert_device_order_history_data")
class TestGetOrderHistory:
    """端末と来店セッションで絞り込む結合読み取りを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_reads_only_visible_orders_and_details_in_one_select(self, mysql_session) -> None:
        """削除済みと別店舗・別セッションの注文を除外し、明細を一括参照する。

        Args:
            mysql_session: MySQLに接続するSQLAlchemyセッション。

        Returns:
            なし。
        """
        connection = mysql_session.connection()
        statements = []

        def _record_statement(conn, cursor, statement, parameters, context, executemany):
            """実行されたSQLを記録する。"""
            statements.append(statement)

        event.listen(connection, "before_cursor_execute", _record_statement)
        try:
            rows = DeviceOrderRepository().get_order_history(mysql_session, ACTIVE_DEVICE, 892001)
        finally:
            event.remove(connection, "before_cursor_execute", _record_statement)

        statement, = statements
        assert statement.lstrip().upper().startswith("SELECT")
        assert statement.upper().count("LEFT OUTER JOIN") == 4
        assert [order.menu_order_id for _, order, _, _ in rows] == [893001, 893001, 893001, 893003, 893002]
        assert [item.menu_order_item_id if item else None for _, _, item, _ in rows] == [
            894002, 894002, 894001, None, None,
        ]
        assert [option.menu_order_item_option_id if option else None for _, _, _, option in rows] == [
            895002, 895001, None, None, None,
        ]

    @pytest.mark.parametrize("device_uuid", [
        "89100400-0000-4000-8000-000000891004",
        "89100500-0000-4000-8000-000000891005",
        "89100600-0000-4000-8000-000000891006",
        "89109900-0000-4000-8000-000000891099",
    ])
    def test_unavailable_device_has_no_rows(self, mysql_session, device_uuid) -> None:
        """利用できない端末は起点となる行から除外する。

        Args:
            mysql_session: MySQLに接続するSQLAlchemyセッション。
            device_uuid: 利用できない端末UUID。

        Returns:
            なし。
        """
        assert DeviceOrderRepository().get_order_history(mysql_session, device_uuid, 892001) == []

    @pytest.mark.parametrize("visit_session_id", [892002, 892004, 892099])
    def test_keeps_device_row_without_accessible_session(self, mysql_session, visit_session_id) -> None:
        """セッション条件を満たさなくても端末行を維持する。

        Args:
            mysql_session: MySQLに接続するSQLAlchemyセッション。
            visit_session_id: 参照対象外の来店セッションID。

        Returns:
            なし。
        """
        rows = DeviceOrderRepository().get_order_history(mysql_session, ACTIVE_DEVICE, visit_session_id)

        assert [tuple(row) for row in rows] == [(None, None, None, None)]

    def test_keeps_checkout_session_row_without_visible_orders(self, mysql_session) -> None:
        """決済処理中のセッションで注文が0件ならセッションIDだけを返す。

        Args:
            mysql_session: MySQLに接続するSQLAlchemyセッション。

        Returns:
            なし。
        """
        rows = DeviceOrderRepository().get_order_history(mysql_session, CHECKOUT_DEVICE, 892003)

        assert [tuple(row) for row in rows] == [(892003, None, None, None)]
