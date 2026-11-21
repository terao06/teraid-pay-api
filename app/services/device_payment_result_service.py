"""端末会計の決済結果を照会し、決済と注文の状態を一括で確定する。"""

from app.core.exceptions.custom_exception import PaymentRequestNotFoundException, UnauthorizedException
from app.middlewares.transaction import get_mysql_db
from app.models.mysql.device import Device
from app.models.mysql.menu_checkout import CheckoutStatus
from app.models.mysql.menu_order import CHECKOUT_UNPAID_STATUSES
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSessionStatus
from app.models.responses.device_payment_result_response import DevicePaymentResultResponse
from app.repositories.mysql.device_payment_repository import DevicePaymentRepository
from app.repositories.mysql.device_repository import DeviceRepository
from app.repositories.mysql.visit_session_repository import VisitSessionRepository
from app.services.device_payment_service import verify_checkout_payment_on_chain


_PENDING_STATUSES = (PaymentStatus.REQUESTED, PaymentStatus.SUBMITTED, PaymentStatus.CONFIRMING)


class DevicePaymentResultService:
    """決済結果の参照、チェーン照会、確定時の状態更新を担当する。

    Args:
        なし。

    Returns:
        端末向け決済結果確認サービス。
    """

    def verify_payment(
        self, device_uuid: str, checkout_id: int, payment_request_id: int
    ) -> DevicePaymentResultResponse:
        """認証済み端末が所有する会計の決済結果を確認する。

        Args:
            device_uuid: 検証済みトークンの端末UUID。
            checkout_id: 端末が決済を開始した会計ID。
            payment_request_id: 会計に紐づく決済試行ID。

        Returns:
            決済状態と現在の来店セッション状態。

        Raises:
            UnauthorizedException: 端末が利用できない場合。
            PaymentRequestNotFoundException: 所有する会計または決済試行が見つからない場合。
            DevicePaymentRpcUnavailable: チェーンへの照会が失敗した場合。
            RuntimeError: 決済確定に必要なデータに不整合がある場合。
        """
        mysql = get_mysql_db()
        with mysql.get_session() as session:
            device = DeviceRepository().get_device_by_uuid(session, device_uuid)
            self._require_active_device(device)
            target = DevicePaymentRepository().get_payment_for_result(
                session, device.device_id, device.store_id, checkout_id, payment_request_id,
            )
            if target is None:
                raise PaymentRequestNotFoundException()
            payment, visit = target
            visit_id, visit_status = visit.visit_session_id, visit.status
            if payment.status not in _PENDING_STATUSES:
                return self._response(payment_request_id, payment.status, visit_status)
            if not payment.checkout_transaction_hash:
                return self._response(payment_request_id, PaymentStatus.CONFIRMING, visit_status)
            session.expunge(payment)

        status = verify_checkout_payment_on_chain(payment)
        if status == PaymentStatus.CONFIRMING:
            return self._response(payment_request_id, status, visit_status)
        return self._finalize(device_uuid, visit_id, payment, status)

    def _finalize(
        self, device_uuid: str, visit_id: int, observed: PaymentRequest, status: PaymentStatus
    ) -> DevicePaymentResultResponse:
        """ロック下で照会時点の決済試行を再確認し、結果を一括更新する。"""
        repository = DevicePaymentRepository()
        with get_mysql_db().get_session() as session, session.begin():
            device = DeviceRepository().get_device_by_uuid_for_update(session, device_uuid)
            self._require_active_device(device)
            visit = VisitSessionRepository().get_visit_session_for_update(session, device.device_id, visit_id)
            if visit is None:
                raise PaymentRequestNotFoundException()
            checkout = repository.get_checkout_for_update(session, observed.checkout_id, visit_id)
            if checkout is None:
                raise PaymentRequestNotFoundException()
            payment = repository.get_payment_for_update(
                session, device.store_id, checkout.checkout_id, observed.payment_request_id,
            )
            if payment is None:
                raise PaymentRequestNotFoundException()
            if payment.status not in _PENDING_STATUSES:
                return self._response(payment.payment_request_id, payment.status, visit.status)
            if payment.checkout_transaction_hash != observed.checkout_transaction_hash:
                return self._response(payment.payment_request_id, PaymentStatus.CONFIRMING, visit.status)
            if (
                visit.status != VisitSessionStatus.CHECKOUT_PROCESSING
                or checkout.status != CheckoutStatus.PROCESSING
                or payment.amount != checkout.total_amount
                or payment.token_symbol != checkout.token_symbol
            ):
                raise RuntimeError("決済試行と会計の状態または金額が一致しません。")

            if status == PaymentStatus.PAID:
                orders = repository.get_checkout_orders_for_update(session, checkout.checkout_id)
                if (
                    not orders
                    or sum(amount for _, amount in orders) != checkout.total_amount
                    or any(
                        order.visit_session_id != visit_id
                        or order.store_id != device.store_id
                        or order.deleted_at is not None
                        or order.paid_at is not None
                        or order.status not in CHECKOUT_UNPAID_STATUSES
                        or order.total_amount != amount
                        or order.token_symbol != checkout.token_symbol
                        for order, amount in orders
                    )
                ):
                    raise RuntimeError("決済に紐づく対象注文が会計の保存内容と一致しません。")
                order_ids = [order.menu_order_id for order, _ in orders]
                if repository.mark_checkout_orders_paid(session, order_ids) != len(order_ids):
                    raise RuntimeError("支払済みへ更新した注文の件数が一致しません。")
                checkout.status = CheckoutStatus.PAID
            else:
                checkout.status = CheckoutStatus.FAILED

            payment.status = status
            repository.update_payment_request(session, payment)
            visit.status = VisitSessionStatus.ACTIVE
            return self._response(payment.payment_request_id, payment.status, visit.status)

    @staticmethod
    def _require_active_device(device: Device | None) -> None:
        """未登録、未有効化または停止中の端末を拒否する。"""
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

    @staticmethod
    def _response(
        payment_request_id: int, status: PaymentStatus, visit_status: VisitSessionStatus
    ) -> DevicePaymentResultResponse:
        """決済試行と応答時点のセッション状態を組み合わせる。"""
        return DevicePaymentResultResponse(
            payment_request_id=payment_request_id, status=status, visit_session_status=visit_status,
        )
