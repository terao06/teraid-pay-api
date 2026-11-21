"""端末注文のMySQLクエリと来店セッションのロックを検証する。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.mysql.visit_session import VisitSession
from app.repositories.mysql.device_order_repository import DeviceOrderRepository
from app.repositories.mysql.visit_session_repository import VisitSessionRepository


_DEVICE_UUID = "86100100-0000-4000-8000-000000861001"
_OTHER_UUID = "86100200-0000-4000-8000-000000861002"


class TestCreateOrder:
    """注文で使用する結合、店舗の絞り込み、排他ロックを実DBで検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.usefixtures("insert_order_list_data")
    def test_gates_saved_details_by_store_and_active_visit(self, mysql_session) -> None:
        """全店舗でキーを照合し、同じ店舗・セッションの明細だけを取得する。

        Args:
            mysql_session: 検証用のMySQLセッション。

        Returns:
            なし。
        """
        repo = DeviceOrderRepository()
        rows = repo.get_order_context(mysql_session, _DEVICE_UUID, 862001, "unserved-pending")
        assert {(row[4].menu_item_id, None if row[5] is None else row[5].menu_option_id) for row in rows} == {
            (863011, None), (863012, 865211), (863012, 865212),
        }
        assert len(rows) == 3
        other_store = repo.get_order_context(mysql_session, _OTHER_UUID, 862002, "unserved-pending")
        assert len(other_store) == 1
        assert other_store[0][3].store_id == 111
        assert tuple(other_store[0][4:]) == (None, None)
        wrong_visit = repo.get_order_context(mysql_session, _OTHER_UUID, 862001, "unserved-pending")
        assert tuple(wrong_visit[0][2:]) == (None, None, None, None)

        replay = repo.get_existing_order(mysql_session, "unserved-pending", 111, 862001)
        assert len(replay) == 3
        assert all(row[0].menu_order_id == 870101 for row in replay)
        assert repo.get_existing_order(mysql_session, "unknown-key", 111, 862001) == []

    @pytest.mark.usefixtures("insert_device_menu_items")
    def test_preserves_unselected_groups_and_rejects_unavailable_catalog(self, mysql_session) -> None:
        """選択がないグループを残し、無効な商品・グループ・オプションを除く。

        Args:
            mysql_session: 検証用のMySQLセッション。

        Returns:
            なし。
        """
        rows = DeviceOrderRepository().get_catalog(
            mysql_session, 111, {863011, 863012, 863014, 863015, 863016}, {865211, 865214, 865215},
        )
        assert {
            (
                item.menu_item_id,
                None if group is None else group.menu_option_group_id,
                None if option is None else option.menu_option_id,
            )
            for item, group, option in rows
        } == {(863011, None, None), (863012, 864111, 865211), (863012, 864112, None), (863012, 864115, None)}

    @pytest.mark.usefixtures("insert_device_order_data")
    def test_locks_active_visit_until_transaction_ends(self, mysql_engine) -> None:
        """ロック中は別の接続が取得できず、ロールバック後に取得できることを確認する。

        Args:
            mysql_engine: 独立したMySQLセッションを作るEngine。

        Returns:
            なし。
        """
        competing_query = (
            select(VisitSession.visit_session_id)
            .where(VisitSession.visit_session_id == 882001)
            .with_for_update(nowait=True)
        )
        with Session(mysql_engine) as locking_session, Session(mysql_engine) as competing_session:
            assert VisitSessionRepository().has_active_visit_session(
                locking_session, 881001, 882001, lock_for_update=True,
            )
            with pytest.raises(OperationalError) as failure:
                competing_session.scalar(competing_query)
            assert failure.value.orig.args[0] == 3572

            competing_session.rollback()
            locking_session.rollback()
            assert competing_session.scalar(competing_query) == 882001
