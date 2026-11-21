"""カテゴリー別メニューの取得条件とMySQLの参照回数を検証する。"""

import pytest
from sqlalchemy import event

from app.repositories.mysql.store_menu_repository import StoreMenuRepository


@pytest.mark.usefixtures("insert_device_menu_items")
class TestGetMenuItemsByCategory:
    """MySQLを使い、カテゴリー起点の外部結合を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_reads_visible_menu_in_one_select(self, mysql_session) -> None:
        """店舗、状態、論理削除を絞り込んで表示順で一括取得する。

        Args:
            mysql_session: DBに接続するSQLAlchemyセッション。

        Returns:
            なし。
        """
        connection = mysql_session.connection()
        statements = []

        def record_statement(conn, cursor, statement, parameters, context, executemany):
            """取得処理が発行したSQLを記録する。"""
            statements.append(statement)

        event.listen(connection, "before_cursor_execute", record_statement)
        try:
            rows = StoreMenuRepository().get_menu_items_by_category(mysql_session, 111, 860012)
            assert [
                (
                    category_id,
                    item.menu_item_id,
                    group.menu_option_group_id if group is not None else None,
                    option.menu_option_id if option is not None else None,
                )
                for category_id, item, group, option in rows
            ] == [
                (860012, 863012, 864115, 865217),
                (860012, 863012, 864111, 865212),
                (860012, 863012, 864111, 865213),
                (860012, 863012, 864111, 865211),
                (860012, 863012, 864112, None),
                (860012, 863013, None, None),
                (860012, 863011, None, None),
            ]
        finally:
            event.remove(connection, "before_cursor_execute", record_statement)

        [statement] = statements
        assert statement.lstrip().upper().startswith("SELECT")
        assert statement.upper().count("LEFT OUTER JOIN") == 3

    def test_returns_category_row_when_all_items_are_unavailable(self, mysql_session) -> None:
        """カテゴリーが有効なら商品が0件でもカテゴリー行を返す。

        Args:
            mysql_session: DBに接続するSQLAlchemyセッション。

        Returns:
            なし。
        """
        rows = StoreMenuRepository().get_menu_items_by_category(mysql_session, 111, 860013)

        assert rows == [(860013, None, None, None)]

    @pytest.mark.parametrize("category_id", [860016, 860014, 860015, 999999])
    def test_returns_no_rows_for_inaccessible_category(self, mysql_session, category_id) -> None:
        """別店舗、無効、削除済み、存在しないカテゴリーを除外する。

        Args:
            mysql_session: DBに接続するSQLAlchemyセッション。
            category_id: 取得対象外のカテゴリーID。

        Returns:
            なし。
        """
        assert StoreMenuRepository().get_menu_items_by_category(mysql_session, 111, category_id) == []
