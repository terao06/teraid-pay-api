"""オーダー一覧サービスの結合行の組み立てを検証する。"""

from datetime import datetime
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from app.models.mysql.menu_order import OrderFulfillmentStatus
from app.services.store_order_service import StoreOrderService


class TestGetOrders:
    """結合された商品・オプションを注文単位へまとめるサービスを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @patch("app.services.store_order_service.StoreOrderRepository")
    def test_builds_order_list(self, mock_repository) -> None:
        """複数の結合行をまとめ、明細や端末のない注文も保持する。

        Args:
            mock_repository: 注文取得リポジトリのモック。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        row = {
            "menu_order_id": 10,
            "visit_session_id": 12,
            "device_name": "客席 1",
            "status": 1,
            "created_at": datetime(2026, 11, 16, 1),
            "served_at": datetime(2026, 11, 16, 1, 30),
            "menu_order_item_id": 13,
            "menu_item_name": "カレー",
            "quantity": 3,
            "menu_order_item_option_id": 14,
            "option_group_name": "トッピング",
            "option_name": "チーズ",
            "option_quantity": 2,
        }
        rows = [
            row,
            dict(row, menu_order_item_option_id=15, option_name="ベーコン", option_quantity=1),
            dict(row, menu_order_id=11, visit_session_id=None, device_name=None, menu_order_item_id=None),
        ]
        repository = mock_repository.return_value
        repository.get_orders.return_value = (rows, 22)

        result = StoreOrderService().get_orders(session, 101, OrderFulfillmentStatus.SERVED, 2, 20)

        repository.get_orders.assert_called_once_with(
            mysql_session=session, store_id=101, fulfillment_status=OrderFulfillmentStatus.SERVED, offset=20, limit=20
        )
        assert result.pagination.model_dump() == {"page": 2, "page_size": 20, "total": 22, "total_pages": 2}
        assert result.orders[0].model_dump(mode="json") == {
            "menu_order_id": 10,
            "visit_session_id": 12,
            "device_name": "客席 1",
            "status": 1,
            "created_at": "2026-11-16T10:00:00+09:00",
            "served_at": "2026-11-16T10:30:00+09:00",
            "items": [
                {
                    "menu_item_name": "カレー",
                    "quantity": 3,
                    "options": [
                        {"option_group_name": "トッピング", "option_name": "チーズ", "option_quantity": 2},
                        {"option_group_name": "トッピング", "option_name": "ベーコン", "option_quantity": 1},
                    ],
                }
            ],
        }
        assert result.orders[1].device_name is None
        assert result.orders[1].items == []
