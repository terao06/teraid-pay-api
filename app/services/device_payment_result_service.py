"""端末会計の決済結果を照会し、決済と注文の状態を一括で確定する。"""

from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import PaymentRequestNotFoundException, UnauthorizedException
from app.middlewares.transaction import get_mysql_db
from app.models.mysql.device import Device
from app.models.mysql.menu_checkout import CheckoutStatus, MenuCheckout
from app.models.mysql.menu_order import CHECKOUT_UNPAID_STATUSES
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.responses.device_payment_result_response import DevicePaymentResultResponse
from app.repositories.mysql.device_order_repository import DeviceOrderRepository
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
            決済状態、現在の来店セッション状態と未払い明細の有無。

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
            visit_id = visit.visit_session_id
            is_pending = payment.status in _PENDING_STATUSES
            response_status = PaymentStatus.CONFIRMING if is_pending else payment.status
            response = self._response(session, payment_request_id, response_status, visit, device.store_id)
            if not is_pending or not payment.checkout_transaction_hash:
                return response
            session.expunge(payment)

        status = verify_checkout_payment_on_chain(payment)
        if status == PaymentStatus.CONFIRMING:
            return response
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
                return self._response(session, payment.payment_request_id, payment.status, visit, device.store_id)
            if payment.checkout_transaction_hash != observed.checkout_transaction_hash:
                return self._response(
                    session, payment.payment_request_id, PaymentStatus.CONFIRMING, visit, device.store_id,
                )
            if (
                visit.status != VisitSessionStatus.CHECKOUT_PROCESSING
                or checkout.status != CheckoutStatus.PROCESSING
                or payment.amount != checkout.total_amount
                or payment.token_symbol != checkout.token_symbol
            ):
                raise RuntimeError("決済試行と会計の状態または金額が一致しません。")

            payment.status = status
            repository.update_payment_request(session, payment)
            paid_quantities = None
            if status == PaymentStatus.PAID:
                paid_quantities = self._apply_paid_checkout(session, repository, checkout, device.store_id)
            else:
                checkout.status = CheckoutStatus.FAILED
            visit.status = VisitSessionStatus.ACTIVE
            return self._response(
                session, payment.payment_request_id, status, visit, device.store_id, paid_quantities=paid_quantities,
            )

    @staticmethod
    def _apply_paid_checkout(
        session: Session, repository: DevicePaymentRepository, checkout: MenuCheckout, store_id: int
    ) -> dict[int, int]:
        """会計明細を検証し、全明細が支払済みの注文を更新して集計済み数量を返す。"""
        checkout_items = repository.get_checkout_items(session, checkout.checkout_id)
        orders = repository.get_checkout_orders_for_update(session, checkout.checkout_id)
        if (
            not checkout_items
            or sum(item.line_amount for item in checkout_items) != checkout.total_amount
            or any(item.quantity <= 0 for item in checkout_items)
            or any(
                order.store_id != store_id
                or order.visit_session_id != checkout.visit_session_id
                or order.deleted_at is not None
                or order.paid_at is not None
                or order.status not in CHECKOUT_UNPAID_STATUSES
                or order.token_symbol != checkout.token_symbol
                for order in orders
            )
        ):
            raise RuntimeError("決済に紐づく対象明細が会計の保存内容と一致しません。")

        order_ids = [order.menu_order_id for order in orders]
        order_items = repository.get_order_items(session, order_ids)
        if not {item.menu_order_item_id for item in checkout_items}.issubset(
            item.menu_order_item_id for item in order_items
        ):
            raise RuntimeError("会計に紐づく注文明細が見つかりません。")

        checkout.status = CheckoutStatus.PAID
        session.flush()
        paid_quantities = DeviceOrderRepository().get_paid_checkout_quantities(session, checkout.visit_session_id)
        fully_paid_order_ids = set(order_ids)
        for item in order_items:
            paid_quantity = paid_quantities.get(item.menu_order_item_id, 0)
            if paid_quantity > item.quantity:
                raise RuntimeError("支払済み数量が注文時の数量を超えています。")
            if paid_quantity < item.quantity:
                fully_paid_order_ids.discard(item.menu_order_id)

        if fully_paid_order_ids:
            updated = repository.mark_checkout_orders_paid(session, sorted(fully_paid_order_ids))
            if updated != len(fully_paid_order_ids):
                raise RuntimeError("支払済みへ更新した注文の件数が一致しません。")
        return paid_quantities

    @staticmethod
    def _require_active_device(device: Device | None) -> None:
        """未登録、未有効化または停止中の端末を拒否する。"""
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

    @staticmethod
    def _response(
        session: Session,
        payment_request_id: int,
        status: PaymentStatus,
        visit: VisitSession,
        store_id: int,
        *,
        paid_quantities: dict[int, int] | None = None,
    ) -> DevicePaymentResultResponse:
        """同じDB参照時点の来店セッション状態と未払い有無を決済結果に添える。"""
        if paid_quantities is None:
            paid_quantities = DeviceOrderRepository().get_paid_checkout_quantities(session, visit.visit_session_id)
        order_items = DevicePaymentRepository().get_unpaid_order_items(session, store_id, visit.visit_session_id)
        return DevicePaymentResultResponse(
            payment_request_id=payment_request_id,
            status=status,
            visit_session_status=visit.status,
            has_unpaid_items=any(quantity > paid_quantities.get(item_id, 0) for item_id, quantity, _ in order_items),
        )
