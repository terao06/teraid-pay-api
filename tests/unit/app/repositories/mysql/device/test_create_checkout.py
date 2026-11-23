"""会計と注文金額の永続化をMySQLで検証する。"""

from decimal import Decimal

import pytest

from app.models.mysql.menu_checkout import CheckoutScope, CheckoutStatus, MenuCheckout
from app.models.mysql.menu_checkout_order import MenuCheckoutOrder
from app.models.mysql.menu_order import MenuOrder
from app.repositories.mysql.device_order_repository import DeviceOrderRepository


@pytest.mark.usefixtures("insert_device_checkout_data")
class TestCreateCheckout:
    """確認待ちの会計と注文金額の登録結果を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_saves_checkout_and_order_amount_in_transaction(self, mysql_session) -> None:
        """採番した会計IDで注文と保存済み金額を関連づける。

        Args:
            mysql_session: 初期化済みのテスト用MySQLセッション。

        Returns:
            なし。
        """
        order = mysql_session.get(MenuOrder, 903002)
        checkout = MenuCheckout(
            visit_session_id=902001, scope=CheckoutScope.ALL_UNPAID,
            total_amount=order.total_amount, token_symbol=order.token_symbol,
        )
        checkout_id = DeviceOrderRepository().create_checkout(mysql_session, checkout, [order])

        assert checkout_id > 0
        assert mysql_session.get(MenuCheckout, checkout_id).status == CheckoutStatus.PENDING_CONFIRMATION
        assert mysql_session.get(MenuCheckoutOrder, (checkout_id, 903002)).order_amount == Decimal("300")
        mysql_session.rollback()
        assert mysql_session.get(MenuCheckout, checkout_id) is None
        assert mysql_session.get(MenuCheckoutOrder, (checkout_id, 903002)) is None
