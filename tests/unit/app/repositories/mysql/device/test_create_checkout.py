"""会計と対象明細の永続化をMySQLで検証する。"""

from decimal import Decimal

import pytest

from app.models.mysql.menu_checkout import CheckoutScope, CheckoutStatus, MenuCheckout
from app.models.mysql.menu_checkout_item import MenuCheckoutItem
from app.models.mysql.menu_checkout_order import MenuCheckoutOrder
from app.repositories.mysql.device_order_repository import DeviceOrderRepository


@pytest.mark.usefixtures("insert_device_checkout_data")
class TestCreateCheckout:
    """確認待ちの会計とその対象明細の登録結果を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("scope", [CheckoutScope.ALL_UNPAID, CheckoutScope.SELECTED_ITEMS])
    def test_saves_checkout_items_in_transaction(self, mysql_session, scope) -> None:
        """対象数量と金額を会計に保存し、まとめ払いには既存決済用の注文情報も登録する。

        Args:
            mysql_session: 初期化済みのテスト用MySQLセッション。
            scope: 登録する確認待ち会計の範囲。

        Returns:
            なし。
        """
        amount = Decimal("300")
        checkout = MenuCheckout(visit_session_id=902001, scope=scope, total_amount=amount, token_symbol="JPYC")
        item = MenuCheckoutItem(menu_order_item_id=907002, quantity=1, line_amount=amount)
        checkout_id = DeviceOrderRepository().create_checkout(mysql_session, checkout, [item], {903002: amount})

        assert checkout_id > 0
        assert mysql_session.get(MenuCheckout, checkout_id).status == CheckoutStatus.PENDING_CONFIRMATION
        saved_item = mysql_session.get(MenuCheckoutItem, (checkout_id, 907002))
        assert (saved_item.quantity, saved_item.line_amount) == (1, amount)
        order = mysql_session.get(MenuCheckoutOrder, (checkout_id, 903002))
        if scope == CheckoutScope.ALL_UNPAID:
            assert order.order_amount == amount
        else:
            assert order is None
        mysql_session.rollback()
        assert mysql_session.get(MenuCheckout, checkout_id) is None
        assert mysql_session.get(MenuCheckoutItem, (checkout_id, 907002)) is None
        assert mysql_session.get(MenuCheckoutOrder, (checkout_id, 903002)) is None
