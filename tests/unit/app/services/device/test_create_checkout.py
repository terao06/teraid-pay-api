"""会計Serviceの対象判定、明細の組み立て、合計金額を検証する。"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    DeviceCheckoutConflictException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_CHECKOUT_ITEM_UNAVAILABLE_ERROR,
    DEVICE_CHECKOUT_MIXED_TOKEN_ERROR,
    DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR,
)
from app.models.mysql.device import Device
from app.models.mysql.menu_checkout import CheckoutScope
from app.models.mysql.menu_order import MenuOrder
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.requests.device_checkout_create_request import (
    DeviceAllUnpaidCheckoutRequest,
    DeviceSelectedItemsCheckoutRequest,
)
from app.services.device_order_service import DeviceOrderService


DEVICE_UUID = "90100100-0000-4000-8000-000000901001"
VISIT_ID = 902001
ALL_UNPAID = DeviceAllUnpaidCheckoutRequest(scope="all_unpaid")


@pytest.fixture()
def checkout_dependencies():
    """利用可能な端末、注文受付中の来店セッション、会計リポジトリを差し替える。

    Args:
        なし。

    Yields:
        MySQLセッションと端末、来店セッション、注文の各リポジトリのモック。
    """
    session = Mock(spec=Session)
    with (
        patch("app.services.device_order_service.DeviceRepository") as devices,
        patch("app.services.device_order_service.VisitSessionRepository") as visits,
        patch("app.services.device_order_service.DeviceOrderRepository") as orders,
    ):
        devices.return_value.get_device_by_uuid_for_update.return_value = Device(
            device_id=901001, store_id=9101, is_active=True, activated_at=datetime(2026, 11, 21),
        )
        visits.return_value.get_visit_session_for_update.return_value = VisitSession(status=VisitSessionStatus.ACTIVE)
        orders.return_value.get_paid_checkout_quantities.return_value = {}
        yield session, devices.return_value, visits.return_value, orders.return_value


class TestCreateCheckout:
    """対象注文の判定と会計への集約を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_groups_order_rows_and_sums_each_item_once(self, checkout_dependencies) -> None:
        """オプションの複数行をまとめて明細・注文・会計の金額を計算する。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。

        Returns:
            なし。
        """
        session, devices, visits, repository = checkout_dependencies
        first = MenuOrder(menu_order_id=1, total_amount=Decimal("1400"), token_symbol="JPYC")
        second = MenuOrder(menu_order_id=2, total_amount=Decimal("300"), token_symbol="JPYC")
        item = MenuOrderItem(
            menu_order_item_id=1, menu_item_name="カレー", unit_price=Decimal("600"),
            quantity=2, line_amount=Decimal("1400"),
        )
        second_item = MenuOrderItem(
            menu_order_item_id=2, menu_item_name="ポテト", unit_price=Decimal("300"),
            quantity=1, line_amount=Decimal("300"),
        )
        repository.get_checkout_orders.return_value = [
            (first, item, MenuOrderItemOption(
                option_group_name="追加", option_name=name, additional_price=Decimal("50"), option_quantity=1,
            ))
            for name in ("チーズ", "ソース")
        ] + [(second, second_item, None)]
        repository.create_checkout.return_value = 7

        response = DeviceOrderService().create_checkout(session, DEVICE_UUID, VISIT_ID, ALL_UNPAID)

        devices.get_device_by_uuid_for_update.assert_called_once_with(session, DEVICE_UUID)
        visits.get_visit_session_for_update.assert_called_once_with(session, 901001, VISIT_ID)
        repository.get_checkout_orders.assert_called_once_with(session, 9101, VISIT_ID)
        repository.get_paid_checkout_quantities.assert_called_once_with(session, VISIT_ID)
        saved_session, checkout, items, order_amounts = repository.create_checkout.call_args.args
        assert saved_session is session
        assert checkout.scope == CheckoutScope.ALL_UNPAID
        assert checkout.total_amount == Decimal("1700")
        assert order_amounts == {1: Decimal("1400"), 2: Decimal("300")}
        assert [(line.menu_order_item_id, line.quantity, line.line_amount) for line in items] == [
            (1, 2, Decimal("1400")), (2, 1, Decimal("300")),
        ]
        assert response.checkout_id == 7
        assert response.total_amount == "1700.000000"
        assert [order.menu_order_id for order in response.orders] == [1, 2]
        saved_item, = response.orders[0].items
        assert saved_item.menu_order_item_id == 1
        assert [option.option_name for option in saved_item.options] == ["チーズ", "ソース"]

    @pytest.mark.parametrize(("visit_status", "expected"), [
        (None, VisitSessionNotFoundException),
        (VisitSessionStatus.CLOSED, VisitSessionNotFoundException),
        (VisitSessionStatus.CHECKOUT_PROCESSING, DeviceCheckoutConflictException),
    ])
    def test_rejects_unavailable_sessions_before_order_read(
        self, checkout_dependencies, visit_status, expected
    ) -> None:
        """会計を開始できない来店セッションでは注文を参照しない。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。
            visit_status: セッションの状態。Noneなら対象セッションなし。
            expected: 期待する業務例外の型。

        Returns:
            なし。
        """
        session, _, visits, repository = checkout_dependencies
        visits.get_visit_session_for_update.return_value = (
            None if visit_status is None else VisitSession(status=visit_status)
        )
        with pytest.raises(expected):
            DeviceOrderService().create_checkout(session, DEVICE_UUID, VISIT_ID, ALL_UNPAID)
        repository.get_checkout_orders.assert_not_called()
        repository.create_checkout.assert_not_called()

    def test_rejects_unavailable_device_before_session_read(self, checkout_dependencies) -> None:
        """使えない端末からのリクエストでは来店セッションを参照しない。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。

        Returns:
            なし。
        """
        session, devices, visits, repository = checkout_dependencies
        devices.get_device_by_uuid_for_update.return_value = None
        with pytest.raises(UnauthorizedException):
            DeviceOrderService().create_checkout(session, DEVICE_UUID, VISIT_ID, ALL_UNPAID)
        visits.get_visit_session_for_update.assert_not_called()
        repository.create_checkout.assert_not_called()

    @pytest.mark.parametrize(("tokens", "message"), [
        ([], DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR),
        (["JPYC", "OTHER"], DEVICE_CHECKOUT_MIXED_TOKEN_ERROR),
    ])
    def test_rejects_empty_or_mixed_token_orders(self, checkout_dependencies, tokens, message) -> None:
        """一括会計で未払い注文がないか通貨が混在するときは会計を保存しない。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。
            tokens: 検索結果の注文ごとのトークンシンボル。
            message: 期待する業務エラーメッセージ。

        Returns:
            なし。
        """
        session, _, _, repository = checkout_dependencies
        repository.get_checkout_orders.return_value = [
            (
                MenuOrder(menu_order_id=order_id, token_symbol=token),
                MenuOrderItem(
                    menu_order_item_id=order_id, menu_item_name="商品", unit_price=Decimal("500"), quantity=1,
                ),
                None,
            )
            for order_id, token in enumerate(tokens, start=1)
        ]
        with pytest.raises(DeviceCheckoutConflictException, match=message):
            DeviceOrderService().create_checkout(session, DEVICE_UUID, VISIT_ID, ALL_UNPAID)
        repository.create_checkout.assert_not_called()

    def test_prices_only_selected_quantity_at_saved_prices(self, checkout_dependencies) -> None:
        """対象外の通貨を含めず、指定数量に注文時の単価とオプション料金を適用する。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。

        Returns:
            なし。
        """
        session, _, _, repository = checkout_dependencies
        order = MenuOrder(menu_order_id=1, token_symbol="JPYC")
        selected_item = MenuOrderItem(
            menu_order_item_id=1, menu_item_name="カレー", unit_price=Decimal("600"), quantity=4,
        )
        option = MenuOrderItemOption(
            option_group_name="追加", option_name="チーズ", additional_price=Decimal("25.125"), option_quantity=2,
        )
        other_order = MenuOrder(menu_order_id=2, token_symbol="OTHER")
        other_item = MenuOrderItem(
            menu_order_item_id=2, menu_item_name="ドリンク", unit_price=Decimal("300"), quantity=1,
        )
        repository.get_checkout_orders.return_value = [(order, selected_item, option), (other_order, other_item, None)]
        repository.get_paid_checkout_quantities.return_value = {1: 2}
        repository.create_checkout.return_value = 7
        request = DeviceSelectedItemsCheckoutRequest(
            scope="selected_items", items=[{"menu_order_item_id": 1, "quantity": 1}],
        )

        response = DeviceOrderService().create_checkout(session, DEVICE_UUID, VISIT_ID, request)

        _, checkout, items, order_amounts = repository.create_checkout.call_args.args
        assert checkout.scope == CheckoutScope.SELECTED_ITEMS
        assert checkout.total_amount == Decimal("650.250")
        assert order_amounts == {1: Decimal("650.250")}
        saved_item, = items
        assert (saved_item.menu_order_item_id, saved_item.quantity, saved_item.line_amount) == (1, 1, Decimal("650.250"))
        order_response, = response.orders
        assert order_response.total_amount == response.total_amount == "650.250000"
        assert response.token_symbol == "JPYC"
        assert order_response.items[0].quantity == 1

    @pytest.mark.parametrize(("item_id", "quantity"), [(1, 3), (2, 1)])
    def test_rejects_selected_items_outside_unpaid_scope(self, checkout_dependencies, item_id, quantity) -> None:
        """未払い数量を超える指定や、対象外の明細を保存前に拒否する。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。
            item_id: リクエストで指定する明細ID。
            quantity: リクエストで指定する数量。

        Returns:
            なし。
        """
        session, _, _, repository = checkout_dependencies
        order = MenuOrder(menu_order_id=1, token_symbol="JPYC")
        item = MenuOrderItem(menu_order_item_id=1, menu_item_name="商品", unit_price=Decimal("600"), quantity=4)
        repository.get_checkout_orders.return_value = [(order, item, None)]
        repository.get_paid_checkout_quantities.return_value = {1: 2}
        request = DeviceSelectedItemsCheckoutRequest(
            scope="selected_items", items=[{"menu_order_item_id": item_id, "quantity": quantity}],
        )

        with pytest.raises(DeviceCheckoutConflictException, match=DEVICE_CHECKOUT_ITEM_UNAVAILABLE_ERROR):
            DeviceOrderService().create_checkout(session, DEVICE_UUID, VISIT_ID, request)
        repository.create_checkout.assert_not_called()
