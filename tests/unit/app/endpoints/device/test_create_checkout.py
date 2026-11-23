"""端末用会計作成APIの入力、認証、永続化をHTTPから検証する。"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import (
    DEVICE_CHECKOUT_ITEM_UNAVAILABLE_ERROR,
    DEVICE_CHECKOUT_MIXED_TOKEN_ERROR,
    DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR,
    DEVICE_CHECKOUT_PROCESSING_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
)
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.mysql.menu_checkout import CheckoutScope, CheckoutStatus, MenuCheckout
from app.models.mysql.menu_checkout_item import MenuCheckoutItem
from app.models.mysql.menu_checkout_order import MenuCheckoutOrder
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.repositories.mysql.device_order_repository import DeviceOrderRepository


PATH = "/device/visit-sessions/{visit_id}/checkouts"
AUTH = DeviceAuthConfig("test-device-jwt-secret-at-least-32-characters", 300)
ALL_UNPAID = {"scope": "all_unpaid"}


def _headers(device_id: int = 901001) -> dict[str, str]:
    """指定端末のテスト用アクセストークンをBearerヘッダーに設定する。"""
    uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
    return {"Authorization": f"Bearer {DeviceAuthUtil.create_access_token(uuid, AUTH)}"}


class TestCreateCheckout:
    """デバイスの会計作成のHTTP契約と登録結果を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("visit_id", "body"), [
        ("0", ALL_UNPAID),
        ("9223372036854775808", ALL_UNPAID),
        (902001, {}),
        (902001, {"scope": "unknown"}),
        (902001, {"scope": "all_unpaid", "menu_order_id": None}),
        (902001, {"scope": "all_unpaid", "menu_order_id": 903001}),
        (902001, {"scope": "single_order"}),
        (902001, {"scope": "single_order", "menu_order_id": 903001}),
        (902001, {"scope": "all_unpaid", "items": None}),
        (902001, {"scope": "all_unpaid", "items": []}),
        (902001, {"scope": "selected_items"}),
        (902001, {"scope": "selected_items", "items": []}),
        (902001, {"scope": "selected_items", "items": [{"menu_order_item_id": 907001, "quantity": 0}]}),
        (902001, {"scope": "selected_items", "items": [{"menu_order_item_id": 907001, "quantity": "1"}]}),
        (902001, {"scope": "selected_items", "items": [{"menu_order_item_id": 907001, "quantity": True}]}),
        (902001, {"scope": "selected_items", "items": [{"menu_order_item_id": 907001, "quantity": 4294967296}]}),
        (902001, {"scope": "selected_items", "items": [{"menu_order_item_id": 9223372036854775808, "quantity": 1}]}),
        (902001, {"scope": "selected_items", "items": [{"menu_order_item_id": 907001, "quantity": 1, "price": 1}]}),
        (902001, {"scope": "selected_items", "items": [
            {"menu_order_item_id": 907001, "quantity": 1}, {"menu_order_item_id": 907001, "quantity": 2},
        ]}),
    ])
    def test_rejects_invalid_input_before_mysql(self, client, visit_id, body) -> None:
        """パスやJSONが不正ならDB接続前に422を返すことを確認する。

        Args:
            client: HTTPクライアント。
            visit_id: パスに指定する来店セッションID。
            body: パスまたはJSONの検証に使うリクエスト本体。

        Returns:
            なし。
        """
        with patch("app.middlewares.transaction.get_mysql_db") as mysql:
            response = client.post(PATH.format(visit_id=visit_id), json=body, headers=_headers())
        assert response.status_code == 422
        assert all("input" not in detail for detail in response.json()["detail"])
        mysql.assert_not_called()

    @pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
    def test_rejects_unauthenticated_requests_before_mysql(self, client, headers) -> None:
        """トークンの欠落と不正をDB接続前に401で返すことを確認する。

        Args:
            client: HTTPクライアント。
            headers: 認証に失敗するヘッダー。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=AUTH),
            patch("app.middlewares.transaction.get_mysql_db") as mysql,
        ):
            response = client.post(PATH.format(visit_id=902001), json=ALL_UNPAID, headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        mysql.assert_not_called()

    @pytest.mark.usefixtures("insert_device_checkout_data")
    def test_with_db_creates_checkout_and_saves_order_amounts(
        self, client_with_db, mysql_session
    ) -> None:
        """未払い注文をすべて会計に保存し、注文時の明細を返すことを確認する。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            mysql_session: APIとは別の確認用MySQLセッション。

        Returns:
            なし。
        """
        response = client_with_db.post(PATH.format(visit_id=902001), json=ALL_UNPAID, headers=_headers())

        assert response.status_code == 201
        assert response.headers["Cache-Control"] == "no-store"
        data = response.json()
        assert data["total_amount"] == "1700.000000"
        assert data["token_symbol"] == "JPYC"
        assert [order["menu_order_id"] for order in data["orders"]] == [903001, 903002]
        item, = data["orders"][0]["items"]
        assert item["menu_order_item_id"] == 907001
        assert item["quantity"] == 2
        assert item["menu_item_name"] == "注文時のカレー"
        assert item["line_amount"] == "1400.000000"
        assert [option["option_name"] for option in item["options"]] == ["注文時のチーズ", "注文時のソース"]
        assert data["orders"][1]["items"][0]["options"] == []

        checkout = mysql_session.get(MenuCheckout, data["checkout_id"])
        assert checkout.visit_session_id == 902001
        assert checkout.scope == CheckoutScope.ALL_UNPAID
        assert checkout.status == CheckoutStatus.PENDING_CONFIRMATION
        assert checkout.total_amount == Decimal("1700.000000")
        assert checkout.token_symbol == "JPYC"
        links = mysql_session.scalars(
            select(MenuCheckoutOrder).where(MenuCheckoutOrder.checkout_id == checkout.checkout_id)
        ).all()
        assert {link.menu_order_id: link.order_amount for link in links} == {
            order["menu_order_id"]: Decimal(order["total_amount"]) for order in data["orders"]
        }
        saved_items = mysql_session.scalars(
            select(MenuCheckoutItem).where(MenuCheckoutItem.checkout_id == checkout.checkout_id)
        ).all()
        assert {row.menu_order_item_id: (row.quantity, row.line_amount) for row in saved_items} == {
            907001: (2, Decimal("1400")),
            907002: (1, Decimal("300")),
        }
        assert mysql_session.get(VisitSession, 902001).status == VisitSessionStatus.ACTIVE
        assert mysql_session.get(MenuOrder, 903001).status == OrderStatus.PENDING_PAYMENT

    @pytest.mark.usefixtures("insert_device_checkout_data")
    @pytest.mark.parametrize(("body", "scope", "quantity", "amount"), [
        (ALL_UNPAID, CheckoutScope.ALL_UNPAID, 2, "1300.000000"),
        (
            {"scope": "selected_items", "items": [{"menu_order_item_id": 907005, "quantity": 1}]},
            CheckoutScope.SELECTED_ITEMS, 1, "650.000000",
        ),
    ])
    def test_with_db_creates_one_checkout_for_the_requested_scope(
        self, client_with_db, mysql_session, body, scope, quantity, amount
    ) -> None:
        """残りの未払い全件か指定分で会計を1件だけ作り、対象数量と金額を保存する。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            mysql_session: APIとは別の確認用MySQLセッション。
            body: 支払方法と対象範囲を指定するリクエスト本体。
            scope: 保存される会計範囲。
            quantity: 保存される未払い明細のうち今回支払う数量。
            amount: 保存される明細・注文・会計の金額。

        Returns:
            なし。
        """
        lookup = select(MenuCheckout.checkout_id).where(MenuCheckout.visit_session_id == 902006)
        before = set(mysql_session.scalars(lookup))
        mysql_session.rollback()

        response = client_with_db.post(PATH.format(visit_id=902006), json=body, headers=_headers())

        assert response.status_code == 201
        data = response.json()
        order, = data["orders"]
        item, = order["items"]
        assert item["menu_order_item_id"] == 907005
        assert item["quantity"] == quantity
        assert item["line_amount"] == order["total_amount"] == data["total_amount"] == amount
        assert order["menu_order_id"] == 903011
        checkout_id = data["checkout_id"]
        assert set(mysql_session.scalars(lookup)) - before == {checkout_id}
        checkout = mysql_session.get(MenuCheckout, checkout_id)
        assert checkout.scope == scope
        assert checkout.status == CheckoutStatus.PENDING_CONFIRMATION
        assert checkout.total_amount == Decimal(amount)
        saved_item, = mysql_session.scalars(
            select(MenuCheckoutItem).where(MenuCheckoutItem.checkout_id == checkout_id)
        ).all()
        assert (saved_item.menu_order_item_id, saved_item.quantity, saved_item.line_amount) == (
            907005, quantity, Decimal(amount),
        )

    @pytest.mark.usefixtures("insert_device_checkout_data")
    @pytest.mark.parametrize(("visit_id", "item_id", "quantity"), [
        (902006, 907005, 3),
        (902006, 907006, 1),
        (902001, 907003, 1),
        (902001, 907007, 1),
        (902001, 907008, 1),
        (902001, 907009, 1),
    ])
    def test_with_db_rejects_items_outside_the_current_unpaid_scope(
        self, client_with_db, mysql_session, visit_id, item_id, quantity
    ) -> None:
        """支払済み、削除済み、対象外の明細や未払い数量を超える指定を拒否する。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            mysql_session: APIとは別の確認用MySQLセッション。
            visit_id: 対象の来店セッションID。
            item_id: 拒否される注文明細ID。
            quantity: 指定する支払い数量。

        Returns:
            なし。
        """
        lookup = select(func.count()).select_from(MenuCheckout).where(MenuCheckout.visit_session_id == visit_id)
        before = mysql_session.scalar(lookup)
        mysql_session.rollback()
        selected = {"scope": "selected_items", "items": [{"menu_order_item_id": item_id, "quantity": quantity}]}

        response = client_with_db.post(PATH.format(visit_id=visit_id), json=selected, headers=_headers())

        assert response.status_code == 409
        assert response.json()["detail"]["message"] == DEVICE_CHECKOUT_ITEM_UNAVAILABLE_ERROR
        assert mysql_session.scalar(lookup) == before

    @pytest.mark.usefixtures("insert_device_checkout_data")
    @pytest.mark.parametrize(("device_id", "visit_id", "status", "message"), [
        (901005, 902001, 401, None),
        (901003, 902001, 404, VISIT_SESSION_NOT_FOUND_ERROR),
        (901001, 902002, 404, VISIT_SESSION_NOT_FOUND_ERROR),
        (901002, 902003, 409, DEVICE_CHECKOUT_PROCESSING_ERROR),
        (901003, 902004, 409, DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR),
        (901004, 902005, 409, DEVICE_CHECKOUT_MIXED_TOKEN_ERROR),
    ])
    def test_with_db_rejects_unavailable_checkout_targets(
        self, client_with_db, mysql_session, device_id, visit_id, status, message
    ) -> None:
        """セッション、注文、端末の制約違反では会計を作らずに対応するエラーを返す。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            mysql_session: APIとは別の確認用MySQLセッション。
            device_id: 認証に使用する端末ID。
            visit_id: 対象の来店セッションID。
            status: 期待するHTTPステータス。
            message: 期待するエラーメッセージ。端末認証ではヘッダーを確認する。

        Returns:
            なし。
        """
        count = select(func.count()).select_from(MenuCheckout).where(MenuCheckout.visit_session_id == visit_id)
        before = mysql_session.scalar(count)
        mysql_session.rollback()

        response = client_with_db.post(PATH.format(visit_id=visit_id), json=ALL_UNPAID, headers=_headers(device_id))

        assert response.status_code == status
        if message is None:
            assert response.headers["WWW-Authenticate"] == "Bearer"
        else:
            assert response.json()["detail"]["message"] == message
        assert mysql_session.scalar(count) == before

    @pytest.mark.usefixtures("insert_device_checkout_data")
    def test_with_db_rolls_back_checkout_and_links_together(self, client_with_db, mysql_session) -> None:
        """会計と明細、既存決済用の注文金額の登録後に失敗するとすべてロールバックする。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            mysql_session: APIとは別の確認用MySQLセッション。

        Returns:
            なし。
        """
        create_checkout = DeviceOrderRepository.create_checkout
        checkout_ids = []

        def _write_then_fail(repository, *args, **kwargs):
            """会計とその明細をDBに書き込んだ後で例外を発生させる。"""
            checkout_ids.append(create_checkout(repository, *args, **kwargs))
            raise RuntimeError("checkout failed after flush")

        with patch.object(DeviceOrderRepository, "create_checkout", _write_then_fail):
            response = client_with_db.post(PATH.format(visit_id=902001), json=ALL_UNPAID, headers=_headers())

        assert response.status_code == 500
        checkout_id, = checkout_ids
        assert mysql_session.get(MenuCheckout, checkout_id) is None
        assert mysql_session.get(MenuCheckoutOrder, (checkout_id, 903001)) is None
        assert mysql_session.get(MenuCheckoutItem, (checkout_id, 907001)) is None
