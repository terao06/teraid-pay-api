"""注文履歴取得の業務判定と明細の組み立てを検証する。"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import UnauthorizedException, VisitSessionNotFoundException
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.services.device_order_service import DeviceOrderService


DEVICE_UUID = "89100100-0000-4000-8000-000000891001"
VISIT_ID = 892001


class TestGetOrderHistory:
    """結合結果の区分と階層化を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("rows", "error"), [
        ([], UnauthorizedException),
        ([(None, None, None, None)], VisitSessionNotFoundException),
    ])
    def test_distinguishes_unavailable_device_and_session(self, rows, error) -> None:
        """端末なしとセッションなしを別々の例外に変換する。

        Args:
            rows: リポジトリが返す結合結果。
            error: 期待する業務例外の型。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        with patch("app.services.device_order_service.DeviceOrderRepository") as repo:
            repo.return_value.get_order_history.return_value = rows
            with pytest.raises(error):
                DeviceOrderService().get_order_history(session, DEVICE_UUID, VISIT_ID)
        repo.return_value.get_order_history.assert_called_once_with(session, DEVICE_UUID, VISIT_ID)

    def test_returns_empty_orders_for_present_session(self) -> None:
        """セッションがあり注文列がNoneなら空配列を返す。

        Args:
            なし。

        Returns:
            なし。
        """
        with patch("app.services.device_order_service.DeviceOrderRepository") as repo:
            repo.return_value.get_order_history.return_value = [(VISIT_ID, None, None, None)]
            result = DeviceOrderService().get_order_history(Mock(spec=Session), DEVICE_UUID, VISIT_ID)
        assert result.orders == []

    def test_groups_saved_items_and_options(self) -> None:
        """オプションで重複する商品をまとめ、保存済みの名称と価格を返す。

        Args:
            なし。

        Returns:
            なし。
        """
        created_at = datetime(2026, 11, 21, 3)
        order = MenuOrder(
            menu_order_id=1, created_at=created_at, status=OrderStatus.PAID,
            total_amount=Decimal("1400"), token_symbol="JPYC",
        )
        item = MenuOrderItem(
            menu_order_item_id=2, menu_item_name="保存済みの商品", unit_price=Decimal("600"),
            quantity=2, line_amount=Decimal("1400"),
        )
        first_option = MenuOrderItemOption(
            menu_order_item_option_id=3, option_group_name="保存済みのグループ", option_name="チーズ",
            additional_price=Decimal("80"), option_quantity=1,
        )
        second_option = MenuOrderItemOption(
            menu_order_item_option_id=4, option_group_name="保存済みのグループ", option_name="ソース",
            additional_price=Decimal("10"), option_quantity=2,
        )

        with patch("app.services.device_order_service.DeviceOrderRepository") as repo:
            repo.return_value.get_order_history.return_value = [
                (VISIT_ID, order, item, first_option),
                (VISIT_ID, order, item, second_option),
            ]
            history = DeviceOrderService().get_order_history(Mock(spec=Session), DEVICE_UUID, VISIT_ID)

        entry, = history.orders
        saved_item, = entry.items
        assert entry.status == OrderStatus.PAID
        assert entry.created_at == created_at.replace(tzinfo=timezone.utc)
        assert entry.total_amount == "1400.000000"
        assert saved_item.menu_item_name == "保存済みの商品"
        assert saved_item.unit_price == "600.000000"
        assert saved_item.line_amount == "1400.000000"
        assert [option.option_name for option in saved_item.options] == ["チーズ", "ソース"]
        assert saved_item.options[1].option_quantity == 2
        assert saved_item.options[1].additional_price == "10.000000"
