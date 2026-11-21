"""顔照合前後の会計再照合と試行の再送判定を検証する。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import DeviceCheckoutConflictException, WalletMismatchException
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

    @pytest.mark.parametrize("existing", [False, True])
    def test_revalidates_under_lock_after_face_lookup(self, existing) -> None:
        """照合後に再送を判定し、新規試行の場合は現在の注文金額を再照合する。

        Args:
            existing: ロック取得までに別のAPI呼び出しが試行を登録した場合はTrue。

        Returns:
            なし。
        """
        device = SimpleNamespace(device_id=1, store_id=101, activated_at=True, is_active=True)
        visit = SimpleNamespace(visit_session_id=2, status=VisitSessionStatus.ACTIVE)
        checkout = SimpleNamespace(
            checkout_id=3,
            scope=CheckoutScope.ALL_UNPAID,
            status=CheckoutStatus.PENDING_CONFIRMATION,
            token_symbol="JPYC",
            total_amount=Decimal("120"),
        )
        registered = SimpleNamespace(payment_request_id=4, status=PaymentStatus.REQUESTED) if existing else None
        with (
            patch(f"{SERVICE}.get_mysql_db") as mysql,
            patch(f"{SERVICE}.get_postgres_db"),
            patch(f"{SERVICE}.DeviceRepository") as devices,
            patch(f"{SERVICE}.VisitSessionRepository") as visits,
            patch(f"{SERVICE}.DevicePaymentRepository") as checkouts,
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
            repository.get_checkout_snapshot.return_value = [
                SimpleNamespace(menu_order_id=10, order_amount=Decimal("120")),
            ]
            repository.get_unpaid_orders.side_effect = [
                [SimpleNamespace(menu_order_id=10, total_amount=Decimal("120"), token_symbol="JPYC")],
                [SimpleNamespace(menu_order_id=10, total_amount=Decimal("130"), token_symbol="JPYC")],
            ]
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
            assert repository.get_unpaid_orders.call_count == (1 if existing else 2)
            identify_payer.assert_called_once()
            build_payment.assert_not_called()
            prepare_payment.assert_not_called()

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
