"""支払済み会計の注文明細ごとの数量集計をMySQLで検証する。"""

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.device_order_repository import DeviceOrderRepository


@pytest.mark.usefixtures("insert_device_checkout_data")
class TestGetPaidCheckoutQuantities:
    """来店セッション内の支払済み数量だけを集計することを確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("visit_session_id", "expected"), [(902006, {907005: 2, 907006: 1}), (902001, {})])
    def test_sums_paid_quantities_by_item(
        self, mysql_session: Session, visit_session_id: int, expected: dict[int, int]
    ) -> None:
        """複数の会計を明細ごとに合計し、未確定・失敗・別セッションの会計を除外する。

        Args:
            mysql_session: 初期化済みのテスト用MySQLセッション。
            visit_session_id: 集計対象の来店セッションID。
            expected: 期待する明細IDと支払済み数量の辞書。

        Returns:
            なし。
        """
        assert DeviceOrderRepository().get_paid_checkout_quantities(mysql_session, visit_session_id) == expected
