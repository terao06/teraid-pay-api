"""決済結果確認サービスのセッション境界と確定競合を検証する。"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSessionStatus
from app.services.device_payment_result_service import DevicePaymentResultService

_SERVICE = "app.services.device_payment_result_service"


class TestVerifyDevicePayment:
    """先に確定した状態を保持し、外部照会時のDB処理を分離することを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("stored_status", "hash_value", "expected"), [
        (PaymentStatus.PAID, "stored-hash", PaymentStatus.PAID),
        (PaymentStatus.ERROR, None, PaymentStatus.ERROR),
        (PaymentStatus.REQUESTED, None, PaymentStatus.CONFIRMING),
        (PaymentStatus.SUBMITTED, "stored-hash", PaymentStatus.CONFIRMING),
    ])
    def test_reads_without_locks_and_closes_session_before_rpc(
        self, stored_status: PaymentStatus, hash_value: str | None, expected: PaymentStatus,
    ) -> None:
        """確定済みや準備中の試行はDBだけで応答し、RPC実行前にはDBを閉じる。

        Args:
            stored_status: 決済試行の保存状態。
            hash_value: 保存済みの送信ハッシュ。
            expected: APIが返す決済状態。

        Returns:
            なし。
        """
        payment = PaymentRequest(status=stored_status, checkout_transaction_hash=hash_value)
        visit_status = VisitSessionStatus.CLOSED if stored_status == PaymentStatus.PAID else VisitSessionStatus.ACTIVE
        visit = SimpleNamespace(visit_session_id=7, status=visit_status)
        device = SimpleNamespace(device_id=1, store_id=2, activated_at=True, is_active=True)
        with (
            patch(f"{_SERVICE}.get_mysql_db") as mysql,
            patch(f"{_SERVICE}.DeviceRepository") as devices,
            patch(f"{_SERVICE}.DevicePaymentRepository") as payments,
            patch(f"{_SERVICE}.verify_checkout_payment_on_chain") as rpc,
        ):
            session_context = mysql.return_value.get_session.return_value

            def chain_check(observed: PaymentRequest) -> PaymentStatus:
                """RPCがDBセッションの終了後に呼び出されることを確認する。"""
                session_context.__exit__.assert_called_once_with(None, None, None)
                assert observed is payment
                return PaymentStatus.CONFIRMING

            devices.return_value.get_device_by_uuid.return_value = device
            payments.return_value.get_payment_for_result.return_value = (payment, visit)
            rpc.side_effect = chain_check
            result = DevicePaymentResultService().verify_payment("uuid", 3, 8)

        assert (result.status, result.visit_session_status) == (expected, visit_status)
        payments.return_value.get_payment_for_result.assert_called_once_with(
            session_context.__enter__.return_value, 1, 2, 3, 8,
        )
        if stored_status == PaymentStatus.SUBMITTED:
            rpc.assert_called_once_with(payment)
        else:
            rpc.assert_not_called()
        payments.return_value.get_payment_for_update.assert_not_called()

    def test_returns_concurrent_result_without_rewriting(self) -> None:
        """RPC照会中に確定された結果を再読込し、上書きしない。

        Args:
            なし。

        Returns:
            なし。
        """
        observed = PaymentRequest(
            payment_request_id=8, checkout_id=3, status=PaymentStatus.SUBMITTED, checkout_transaction_hash="hash",
        )
        terminal = PaymentRequest(payment_request_id=8, status=PaymentStatus.PAID)
        device = SimpleNamespace(device_id=1, store_id=2, activated_at=True, is_active=True)
        checkout = SimpleNamespace(checkout_id=3)
        visit = SimpleNamespace(visit_session_id=7, status=VisitSessionStatus.CLOSED)
        with (
            patch(f"{_SERVICE}.get_mysql_db"),
            patch(f"{_SERVICE}.DeviceRepository") as devices,
            patch(f"{_SERVICE}.VisitSessionRepository") as visits,
            patch(f"{_SERVICE}.DevicePaymentRepository") as payments,
            patch(f"{_SERVICE}.verify_checkout_payment_on_chain", return_value=PaymentStatus.TX_FAILED),
        ):
            devices.return_value.get_device_by_uuid.return_value = device
            devices.return_value.get_device_by_uuid_for_update.return_value = device
            visits.return_value.get_visit_session_for_update.return_value = visit
            payments.return_value.get_payment_for_result.return_value = (observed, visit)
            payments.return_value.get_checkout_for_update.return_value = checkout
            payments.return_value.get_payment_for_update.return_value = terminal

            result = DevicePaymentResultService().verify_payment("uuid", 3, 8)

        assert (result.status, result.visit_session_status) == (PaymentStatus.PAID, VisitSessionStatus.CLOSED)
        payments.return_value.update_payment_request.assert_not_called()
        payments.return_value.mark_checkout_orders_paid.assert_not_called()
