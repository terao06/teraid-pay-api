"""会計Serviceの対象判定、明細の組み立て、合計金額を検証する。"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    DeviceCheckoutConflictException,
    DeviceCheckoutOrderNotFoundException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.models.mysql.device import Device
from app.models.mysql.menu_checkout import CheckoutScope
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.requests.device_checkout_create_request import AllUnpaidCheckoutRequest, SingleOrderCheckoutRequest
from app.services.device_order_service import DeviceOrderService


DEVICE_UUID = "90100100-0000-4000-8000-000000901001"
VISIT_ID = 902001


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
        yield session, devices.return_value, visits.return_value, orders.return_value


class TestCreateCheckout:
    """対象注文の判定と会計への集約を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_groups_order_rows_and_sums_each_order_once(self, checkout_dependencies) -> None:
        """オプションの複数行をまとめて注文単位で合計金額を計算する。

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
        repository.get_checkout_orders.return_value = [
            (first, item, MenuOrderItemOption(
                option_group_name="追加", option_name=name, additional_price=Decimal("50"), option_quantity=1,
            ))
            for name in ("チーズ", "ソース")
        ] + [(second, None, None)]
        repository.create_checkout.return_value = 7

        response = DeviceOrderService().create_checkout(
            session, DEVICE_UUID, VISIT_ID, AllUnpaidCheckoutRequest(scope="all_unpaid"),
        )

        devices.get_device_by_uuid_for_update.assert_called_once_with(session, DEVICE_UUID)
        visits.get_visit_session_for_update.assert_called_once_with(session, 901001, VISIT_ID)
        repository.get_checkout_orders.assert_called_once_with(session, 9101, VISIT_ID, None)
        saved_session, checkout, orders = repository.create_checkout.call_args.args
        assert saved_session is session
        assert checkout.scope == CheckoutScope.ALL_UNPAID
        assert checkout.total_amount == Decimal("1700")
        assert orders == [first, second]
        assert response.checkout_id == 7
        assert response.total_amount == "1700.000000"
        assert [order.menu_order_id for order in response.orders] == [1, 2]
        saved_item, = response.orders[0].items
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
            DeviceOrderService().create_checkout(
                session, DEVICE_UUID, VISIT_ID, AllUnpaidCheckoutRequest(scope="all_unpaid"),
            )
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
            DeviceOrderService().create_checkout(
                session, DEVICE_UUID, VISIT_ID, AllUnpaidCheckoutRequest(scope="all_unpaid"),
            )
        visits.get_visit_session_for_update.assert_not_called()
        repository.create_checkout.assert_not_called()

    @pytest.mark.parametrize(("status", "paid_at", "expected"), [
        (None, None, DeviceCheckoutOrderNotFoundException),
        (OrderStatus.PAID, None, DeviceCheckoutConflictException),
        (OrderStatus.CANCELED, None, DeviceCheckoutConflictException),
        (OrderStatus.PAYMENT_PROCESSING, None, DeviceCheckoutConflictException),
        (OrderStatus.PENDING_PAYMENT, datetime(2026, 11, 21), DeviceCheckoutConflictException),
    ])
    def test_distinguishes_missing_and_non_payable_single_order(
        self, checkout_dependencies, status, paid_at, expected
    ) -> None:
        """注文が存在しない場合と、存在しても会計対象外の場合を区別する。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。
            status: 注文の状態。Noneなら対象注文なし。
            paid_at: 記録済みの決済完了日時。
            expected: 期待する業務例外の型。

        Returns:
            なし。
        """
        session, _, _, repository = checkout_dependencies
        repository.get_checkout_orders.return_value = (
            [] if status is None else [(MenuOrder(menu_order_id=1, status=status, paid_at=paid_at), None, None)]
        )
        with pytest.raises(expected):
            DeviceOrderService().create_checkout(
                session, DEVICE_UUID, VISIT_ID, SingleOrderCheckoutRequest(scope="single_order", menu_order_id=1),
            )
        repository.get_checkout_orders.assert_called_once_with(session, 9101, VISIT_ID, 1)
        repository.create_checkout.assert_not_called()

    @pytest.mark.parametrize("tokens", [[], ["JPYC", "OTHER"]])
    def test_rejects_empty_or_mixed_token_orders(self, checkout_dependencies, tokens) -> None:
        """一括会計で未払い注文がないか通貨が混在するときは会計を保存しない。

        Args:
            checkout_dependencies: セッションとリポジトリのモック。
            tokens: 検索結果の注文ごとのトークンシンボル。

        Returns:
            なし。
        """
        session, _, _, repository = checkout_dependencies
        repository.get_checkout_orders.return_value = [
            (MenuOrder(menu_order_id=order_id, token_symbol=token), None, None)
            for order_id, token in enumerate(tokens, start=1)
        ]
        with pytest.raises(DeviceCheckoutConflictException):
            DeviceOrderService().create_checkout(
                session, DEVICE_UUID, VISIT_ID, AllUnpaidCheckoutRequest(scope="all_unpaid"),
            )
        repository.create_checkout.assert_not_called()
