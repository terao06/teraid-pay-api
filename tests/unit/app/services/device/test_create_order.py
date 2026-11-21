"""注文Serviceの価格計算、受付条件、保存済み明細の照合を検証する。"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    DeviceOrderConflictException,
    DeviceOrderInvalidException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.models.mysql.device import Device
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.models.requests.device_order_create_request import DeviceOrderCreateRequest
from app.services.device_order_service import DeviceOrderService


_DEVICE_UUID = "88100100-0000-4000-8000-000000881001"
_REQUEST = DeviceOrderCreateRequest(items=[{
    "menu_item_id": 10,
    "quantity": 2,
    "options": [{"menu_option_id": 30, "option_quantity": 2}],
}])


@pytest.fixture()
def order_dependencies():
    """注文のDB依存をモックし、販売商品と注文可能なセッションを準備する。

    Args:
        なし。

    Returns:
        MySQLセッションと各リポジトリのモックを提供するフィクスチャー。
    """
    with (
        patch("app.services.device_order_service.DeviceOrderRepository") as order_class,
        patch("app.services.device_order_service.DeviceRepository") as device_class,
        patch("app.services.device_order_service.VisitSessionRepository") as visit_class,
    ):
        orders = order_class.return_value
        devices = device_class.return_value
        visits = visit_class.return_value
        orders.get_order_context.return_value = [(101, 113, 401, None, None, None)]
        orders.get_catalog.return_value = [
            (
                MenuItem(menu_item_id=10, name="バーガー", price=Decimal("651.25"), token_symbol="JPYC"),
                MenuOptionGroup(menu_option_group_id=20, name="追加", min_selections=1, max_selections=2),
                MenuOption(menu_option_id=30, name="チーズ", additional_price=Decimal("10.125")),
            ),
        ]
        devices.get_device_by_uuid_for_update.return_value = Device(
            device_id=101, store_id=113, activated_at=Mock(), is_active=True,
        )
        visits.has_active_visit_session.return_value = True
        yield Mock(spec=Session), orders, devices, visits


def _assign_order_id(session, order):
    """INSERTで主キーが割り当てられる動作を再現する。"""
    order.menu_order_id = 123


def _saved_order(store_id=113, visit_session_id=401, option_quantity=2):
    """照合に使用する、カタログとは異なる保存時の価格と明細を作る。"""
    return (
        MenuOrder(menu_order_id=123, store_id=store_id, visit_session_id=visit_session_id,
                  total_amount=Decimal("1500"), token_symbol="JPYC"),
        MenuOrderItem(menu_order_item_id=300, menu_item_id=10, quantity=2),
        MenuOrderItemOption(menu_option_id=30, option_quantity=option_quantity),
    )


class TestCreateOrder:
    """リポジトリをモックして注文の業務条件を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_prices_options_per_item_and_saves_snapshots(self, order_dependencies) -> None:
        """商品単価とオプションの数量から金額を計算し、注文時点の明細を渡す。

        Args:
            order_dependencies: 注文・端末・セッションのモック。

        Returns:
            なし。
        """
        session, orders, devices, visits = order_dependencies
        orders.create_order.side_effect = _assign_order_id

        response, created = DeviceOrderService().create_order(session, _DEVICE_UUID, 401, "key", _REQUEST)

        assert created
        assert response.model_dump() == {"menu_order_id": 123, "total_amount": "1343.000000", "token_symbol": "JPYC"}
        order = orders.create_order.call_args.args[1]
        assert (order.status, order.store_id, order.visit_session_id) == (OrderStatus.PENDING_PAYMENT.value, 113, 401)
        line, options = orders.create_order_items.call_args.args[2][0]
        assert (line.menu_item_name, line.unit_price, line.line_amount) == ("バーガー", Decimal("651.25"), Decimal("1343"))
        assert (options[0].option_group_name, options[0].option_name, options[0].option_quantity) == ("追加", "チーズ", 2)
        devices.get_device_by_uuid_for_update.assert_called_once_with(session, _DEVICE_UUID)
        visits.has_active_visit_session.assert_called_once_with(session, 101, 401, lock_for_update=True)

    @pytest.mark.parametrize(("store_id", "visit_session_id", "option_quantity"), [
        (114, 401, 2), (113, 402, 2), (113, 401, 1),
    ])
    def test_rejects_different_existing_order(self, order_dependencies, store_id, visit_session_id, option_quantity) -> None:
        """店舗・セッション・オプション数量のいずれかが違えば再送を拒否する。

        Args:
            order_dependencies: 注文関連のモック。
            store_id: 保存済みの店舗ID。
            visit_session_id: 保存済みの来店セッションID。
            option_quantity: 保存済みのオプション数量。

        Returns:
            なし。
        """
        session, orders, _, _ = order_dependencies
        orders.get_order_context.return_value = [(101, 113, 401, *_saved_order(store_id, visit_session_id, option_quantity))]
        with pytest.raises(DeviceOrderConflictException):
            DeviceOrderService().create_order(session, _DEVICE_UUID, 401, "key", _REQUEST)
        orders.get_catalog.assert_not_called()
        orders.create_order.assert_not_called()

    @pytest.mark.parametrize(("scenario", "error"), [
        ("required-option-missing", DeviceOrderInvalidException),
        ("device-disabled", UnauthorizedException),
        ("visit-inactive", VisitSessionNotFoundException),
    ])
    def test_rejects_invalid_cart_or_invalidated_visit(self, order_dependencies, scenario, error) -> None:
        """必要な選択や登録直前の受付条件を満たさない場合は保存しない。

        Args:
            order_dependencies: 注文関連のモック。
            scenario: 無効にする業務条件。
            error: 期待する例外クラス。

        Returns:
            なし。
        """
        session, orders, devices, visits = order_dependencies
        request = _REQUEST
        if scenario == "required-option-missing":
            request = DeviceOrderCreateRequest(items=[{"menu_item_id": 10, "quantity": 2, "options": []}])
        elif scenario == "device-disabled":
            devices.get_device_by_uuid_for_update.return_value.is_active = False
        elif scenario == "visit-inactive":
            visits.has_active_visit_session.return_value = False

        with pytest.raises(error):
            DeviceOrderService().create_order(session, _DEVICE_UUID, 401, "key", request)
        orders.create_order.assert_not_called()
        orders.create_order_items.assert_not_called()

    def test_fetches_committed_order_after_duplicate_insert(self, order_dependencies) -> None:
        """重複INSERT後にスナップショットを破棄し、先に確定した注文の保存額を返す。

        Args:
            order_dependencies: 注文関連のモック。

        Returns:
            なし。
        """
        session, orders, _, _ = order_dependencies
        orders.create_order.side_effect = IntegrityError("insert", {}, Exception(1062))
        orders.get_existing_order.return_value = [_saved_order()]

        response, created = DeviceOrderService().create_order(session, _DEVICE_UUID, 401, "key", _REQUEST)

        assert not created
        assert response.total_amount == "1500.000000"
        session.rollback.assert_called_once_with()
        orders.get_existing_order.assert_called_once_with(session, "key", 113, 401)
        orders.create_order_items.assert_not_called()
