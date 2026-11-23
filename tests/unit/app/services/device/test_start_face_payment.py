"""顔照合前後の会計再照合と試行の再送判定を検証する。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import DeviceCheckoutConflictException, WalletMismatchException
from app.core.exceptions.message import DEVICE_CHECKOUT_CHANGED_ERROR
from app.models.mysql.menu_checkout import CheckoutScope, CheckoutStatus
from app.models.mysql.payment_request import PaymentStatus
from app.models.mysql.visit_session import VisitSessionStatus
from app.services.device_payment_service import DevicePaymentService

SERVICE = "app.services.device_payment_service"


class TestStartFacePayment:
    """顔照合中に変化した会計と先に登録された試行を検出する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("change", ["additional_order", "paid_quantity", "existing_payment"])
    def test_revalidates_under_lock_after_face_lookup(self, change) -> None:
        """照合後に追加注文、支払済み数量の変化、先行試行を検出する。

        Args:
            change: ロック取得までに発生する会計または決済試行の変化。

        Returns:
            なし。
        """
        device = SimpleNamespace(device_id=1, store_id=101, activated_at=True, is_active=True)
        visit = SimpleNamespace(visit_session_id=2, status=VisitSessionStatus.ACTIVE)
        checkout = SimpleNamespace(
            checkout_id=3,
            scope=CheckoutScope.SELECTED_ITEMS if change == "paid_quantity" else CheckoutScope.ALL_UNPAID,
            status=CheckoutStatus.PENDING_CONFIRMATION,
            token_symbol="JPYC",
            total_amount=Decimal("120"),
        )
        existing = change == "existing_payment"
        registered = SimpleNamespace(payment_request_id=4, status=PaymentStatus.REQUESTED) if existing else None
        with (
            patch(f"{SERVICE}.get_mysql_db") as mysql,
            patch(f"{SERVICE}.get_postgres_db"),
            patch(f"{SERVICE}.DeviceRepository") as devices,
            patch(f"{SERVICE}.VisitSessionRepository") as visits,
            patch(f"{SERVICE}.DevicePaymentRepository") as checkouts,
            patch(f"{SERVICE}.DeviceOrderRepository") as orders,
            patch.object(DevicePaymentService, "_identify_payer") as identify_payer,
            patch.object(DevicePaymentService, "_build_payment_request") as build_payment,
            patch.object(DevicePaymentService, "_prepare_payment") as prepare_payment,
        ):
            session = mysql.return_value.get_session.return_value.__enter__.return_value
            devices.return_value.get_device_by_uuid.return_value = device
            devices.return_value.get_device_by_uuid_for_update.return_value = device
            visits.return_value.get_visit_session_for_update.return_value = visit
            repository = checkouts.return_value
            repository.get_owned_checkout.return_value = (checkout, visit)
            repository.get_checkout_for_update.return_value = checkout
            repository.get_checkout_items.return_value = [
                SimpleNamespace(menu_order_item_id=10, quantity=2, line_amount=Decimal("120")),
            ]
            before = [(10, 2, "JPYC")]
            after = [*before, (11, 1, "JPYC")] if change == "additional_order" else before
            repository.get_unpaid_order_items.side_effect = [before, after]
            paid_after = {10: 1} if change == "paid_quantity" else {}
            orders.return_value.get_paid_checkout_quantities.side_effect = [{}, paid_after]
            repository.get_checkout_payment.side_effect = [None, registered]
            if existing:
                result, status = DevicePaymentService().start_face_payment("device", 3, "key", "image")
                assert (result.payment_request_id, result.status, status) == (4, PaymentStatus.REQUESTED, 200)
            else:
                with pytest.raises(DeviceCheckoutConflictException):
                    DevicePaymentService().start_face_payment("device", 3, "key", "image")
            devices.return_value.get_device_by_uuid_for_update.assert_called_once_with(session, "device")
            visits.return_value.get_visit_session_for_update.assert_called_once_with(session, 1, 2)
            repository.get_checkout_for_update.assert_called_once_with(session, 3, 2)
            assert repository.get_unpaid_order_items.call_count == (1 if existing else 2)
            assert orders.return_value.get_paid_checkout_quantities.call_count == (1 if existing else 2)
            identify_payer.assert_called_once()
            build_payment.assert_not_called()
            prepare_payment.assert_not_called()

    def test_rejects_new_attempt_for_legacy_checkout_before_order_lookup(self) -> None:
        """移行前の個別会計では注文再照合や決済試行の作成に進まない。

        Args:
            なし。

        Returns:
            なし。
        """
        visit = SimpleNamespace(status=VisitSessionStatus.ACTIVE)
        checkout = SimpleNamespace(
            checkout_id=3, scope=CheckoutScope.SINGLE_ORDER, status=CheckoutStatus.PENDING_CONFIRMATION,
        )
        with patch(f"{SERVICE}.DevicePaymentRepository") as checkouts:
            repository = checkouts.return_value
            repository.get_checkout_payment.return_value = None
            with pytest.raises(DeviceCheckoutConflictException, match=DEVICE_CHECKOUT_CHANGED_ERROR):
                DevicePaymentService._find_payment_or_check_checkout(Mock(), Mock(), visit, checkout, b"key")
        repository.get_checkout_items.assert_not_called()
        repository.get_unpaid_order_items.assert_not_called()

    def test_build_payment_rejects_unsupported_checkout_currency(self) -> None:
        """会計通貨がJPYC以外ならウォレットの検索や決済の登録前に拒否する。

        Args:
            なし。

        Returns:
            なし。
        """
        with (
            patch(f"{SERVICE}.StoreWalletRepository") as wallets,
            pytest.raises(WalletMismatchException),
        ):
            DevicePaymentService._build_payment_request(
                Mock(), store_id=101, user_id=107, amount=Decimal("100.25"), token_symbol="USDC"
            )
        wallets.assert_not_called()
