"""来店セッション終了時の未払い注文の検索条件を実DBで検証する。"""

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.device_order_repository import DeviceOrderRepository


@pytest.mark.usefixtures("insert_visit_session_completion_data")
class TestHasUnpaidOrders:
    """注文の状態とセッション・店舗の範囲を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(
        ("store_id", "visit_session_id", "expected"),
        [(9301, 932001, False), (9301, 932002, True), (9301, 932004, True), (9302, 932002, False)],
    )
    def test_matches_only_unpaid_orders_in_store_and_visit(
        self, mysql_session: Session, store_id: int, visit_session_id: int, expected: bool
    ) -> None:
        """支払い待ちと決済失敗を検出し、別店舗・削除済み・支払済み・取消済みを除外する。

        Args:
            mysql_session: 実DBのテスト用セッション。
            store_id: 検索対象の店舗ID。
            visit_session_id: 検索対象の来店セッションID。
            expected: 未払い注文の有無の期待値。

        Returns:
            なし。
        """
        assert DeviceOrderRepository().has_unpaid_orders(mysql_session, store_id, visit_session_id) is expected
