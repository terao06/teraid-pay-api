"""端末決済の会計、対象明細、決済試行を参照・更新する。"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.models.mysql.menu_checkout import MenuCheckout
from app.models.mysql.menu_checkout_item import MenuCheckoutItem
from app.models.mysql.menu_checkout_order import MenuCheckoutOrder
from app.models.mysql.menu_order import CHECKOUT_UNPAID_STATUSES, MenuOrder, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSession


class DevicePaymentRepository:
    """会計の所有端末と決済対象を参照し、端末の決済試行を永続化する。

    Args:
        なし。

    Returns:
        端末の会計を照合するリポジトリ。
    """

    def get_owned_checkout(
        self, mysql_session: Session, checkout_id: int, device_id: int
    ) -> tuple[MenuCheckout, VisitSession] | None:
        """端末が所有する会計と来店セッションを取得する。

        Args:
            mysql_session: 参照用のMySQLセッション。
            checkout_id: 対象の会計ID。
            device_id: 認証済みの端末ID。

        Returns:
            会計と来店セッションの組。対象がなければNone。
        """
        statement = (
            select(MenuCheckout, VisitSession)
            .join(VisitSession, MenuCheckout.visit_session_id == VisitSession.visit_session_id)
            .where(MenuCheckout.checkout_id == checkout_id, VisitSession.device_id == device_id)
        )
        row = mysql_session.execute(statement).tuples().one_or_none()
        return (row[0], row[1]) if row is not None else None

    def get_checkout_for_update(
        self, mysql_session: Session, checkout_id: int, visit_session_id: int
    ) -> MenuCheckout | None:
        """ロック済みの来店セッションに属する会計を排他ロックする。

        Args:
            mysql_session: 登録トランザクションのMySQLセッション。
            checkout_id: ロックする会計ID。
            visit_session_id: 認証済み端末が所有し、ロック済みのセッションID。

        Returns:
            排他ロックした会計。対象がなければNone。
        """
        return mysql_session.scalar(
            select(MenuCheckout)
            .where(MenuCheckout.checkout_id == checkout_id, MenuCheckout.visit_session_id == visit_session_id)
            .with_for_update()
        )

    def get_checkout_items(self, mysql_session: Session, checkout_id: int) -> Sequence[MenuCheckoutItem]:
        """会計作成時に保存した注文明細ID、対象数量、金額を取得する。

        Args:
            mysql_session: 参照用のMySQLセッション。
            checkout_id: 対象の会計ID。

        Returns:
            対象会計に保存された会計明細。
        """
        return mysql_session.scalars(
            select(MenuCheckoutItem).where(MenuCheckoutItem.checkout_id == checkout_id)
        ).all()

    def get_unpaid_order_items(
        self, mysql_session: Session, store_id: int, visit_session_id: int
    ) -> Sequence[tuple[int, int, str]]:
        """認証済み店舗で未払い状態の注文から明細を取得する。

        Args:
            mysql_session: 注文検索のMySQLセッション。
            store_id: 認証済み端末の店舗ID。
            visit_session_id: 認証済み端末の来店セッションID。

        Returns:
            未削除・未払いの注文に属する明細ID、注文時の数量、注文の通貨。
        """
        statement = (
            select(MenuOrderItem.menu_order_item_id, MenuOrderItem.quantity, MenuOrder.token_symbol)
            .join(MenuOrder, MenuOrder.menu_order_id == MenuOrderItem.menu_order_id)
            .where(
                MenuOrder.store_id == store_id,
                MenuOrder.visit_session_id == visit_session_id,
                MenuOrder.deleted_at.is_(None),
                MenuOrder.paid_at.is_(None),
                MenuOrder.status.in_(CHECKOUT_UNPAID_STATUSES),
            )
        )
        return mysql_session.execute(statement).tuples().all()

    def get_checkout_payment(
        self,
        mysql_session: Session,
        checkout_id: int,
        idempotency_key_hash: bytes,
        *,
        include_processing: bool,
    ) -> PaymentRequest | None:
        """同じキーの試行を優先し、必要に応じて会計で処理中の試行を返す。

        Args:
            mysql_session: 決済試行を参照するMySQLセッション。
            checkout_id: 認証済み端末に紐づく会計ID。
            idempotency_key_hash: 再送を識別するキーのSHA-256。
            include_processing: 別のキーで処理中の同じ会計の試行も検索するか。

        Returns:
            一致した決済試行。見つからない場合はNone。
        """
        same_key = PaymentRequest.idempotency_key_hash == idempotency_key_hash
        condition = same_key
        if include_processing:
            condition = or_(same_key, PaymentRequest.status.in_(
                (PaymentStatus.REQUESTED, PaymentStatus.SUBMITTED, PaymentStatus.CONFIRMING)
            ))

        statement = (
            select(PaymentRequest)
            .where(PaymentRequest.checkout_id == checkout_id, PaymentRequest.deleted_at.is_(None), condition)
            .order_by(same_key.desc(), PaymentRequest.payment_request_id.desc())
            .limit(1)
        )
        return mysql_session.scalar(statement)

    def get_requested_payment(
        self, mysql_session: Session, checkout_id: int, payment_request_id: int
    ) -> PaymentRequest | None:
        """指定された会計の未送信試行をロックし、確定処理との更新競合を防ぐ。

        Args:
            mysql_session: 決済試行を更新するトランザクションのMySQLセッション。
            checkout_id: 対象の会計ID。
            payment_request_id: 更新対象の決済試行ID。

        Returns:
            未送信の試行。会計や試行の状態が一致しない場合はNone。
        """
        return mysql_session.scalar(
            select(PaymentRequest).where(
                PaymentRequest.checkout_id == checkout_id,
                PaymentRequest.payment_request_id == payment_request_id,
                PaymentRequest.status == PaymentStatus.REQUESTED,
                PaymentRequest.deleted_at.is_(None),
            ).with_for_update()
        )

    def get_payment_for_result(
        self, mysql_session: Session, device_id: int, store_id: int, checkout_id: int, payment_request_id: int
    ) -> tuple[PaymentRequest, VisitSession] | None:
        """端末が所有する会計の決済試行と現在の来店セッションを一度に取得する。

        Args:
            mysql_session: DB参照用のMySQLセッション。
            device_id: 認証済み端末ID。
            store_id: 端末の所属店舗ID。
            checkout_id: 照会対象の会計ID。
            payment_request_id: 照会対象の決済試行ID。

        Returns:
            未削除の決済試行と来店セッションの組。対象がなければNone。
        """
        statement = (
            select(PaymentRequest, VisitSession)
            .join(MenuCheckout, MenuCheckout.checkout_id == PaymentRequest.checkout_id)
            .join(VisitSession, VisitSession.visit_session_id == MenuCheckout.visit_session_id)
            .where(
                VisitSession.device_id == device_id,
                MenuCheckout.checkout_id == checkout_id,
                PaymentRequest.payment_request_id == payment_request_id,
                PaymentRequest.store_id == store_id,
                PaymentRequest.deleted_at.is_(None),
            )
        )
        row = mysql_session.execute(statement).tuples().one_or_none()
        return (row[0], row[1]) if row is not None else None

    def get_payment_for_update(
        self, mysql_session: Session, store_id: int, checkout_id: int, payment_request_id: int
    ) -> PaymentRequest | None:
        """ロック済みの会計に紐づく決済試行を排他ロックする。

        Args:
            mysql_session: 決済結果を確定するMySQLセッション。
            store_id: 認証済み端末の所属店舗ID。
            checkout_id: ロック済みの会計ID。
            payment_request_id: ロック対象の決済試行ID。

        Returns:
            ロック済みの決済試行。対象がなければNone。
        """
        return mysql_session.scalar(
            select(PaymentRequest).where(
                PaymentRequest.checkout_id == checkout_id,
                PaymentRequest.payment_request_id == payment_request_id,
                PaymentRequest.store_id == store_id,
                PaymentRequest.deleted_at.is_(None),
            ).with_for_update()
        )

    def get_checkout_orders_for_update(
        self, mysql_session: Session, checkout_id: int
    ) -> Sequence[tuple[MenuOrder, Decimal]]:
        """会計の対象注文と保存済み金額を結合して取得し、行をロックする。

        Args:
            mysql_session: 決済結果を確定するMySQLセッション。
            checkout_id: ロック済みの会計ID。

        Returns:
            対象注文と会計時点の注文金額の組。
        """
        statement = (
            select(MenuOrder, MenuCheckoutOrder.order_amount)
            .join(MenuCheckoutOrder, MenuCheckoutOrder.menu_order_id == MenuOrder.menu_order_id)
            .where(MenuCheckoutOrder.checkout_id == checkout_id)
            .with_for_update()
        )
        return mysql_session.execute(statement).tuples().all()

    def mark_checkout_orders_paid(self, mysql_session: Session, order_ids: Sequence[int]) -> int:
        """検証済みの全対象注文を支払済みに更新する。

        Args:
            mysql_session: 対象注文をロック済みのMySQLセッション。
            order_ids: 会計に紐づく検証済みの注文ID。

        Returns:
            支払済みにした注文件数。
        """
        result = mysql_session.execute(
            update(MenuOrder)
            .where(MenuOrder.menu_order_id.in_(order_ids))
            .values(status=OrderStatus.PAID.value, paid_at=func.utc_timestamp())
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    def create_payment_request(self, mysql_session: Session, payment_request: PaymentRequest) -> PaymentRequest:
        """会計に紐づく決済試行を登録し、IDを確定する。

        Args:
            mysql_session: 会計と来店セッションをロックしたMySQLセッション。
            payment_request: 会計と冪等性キーを設定済みの決済試行。

        Returns:
            採番済みの決済試行。
        """
        mysql_session.add(payment_request)
        mysql_session.flush()
        return payment_request

    def update_payment_request(self, mysql_session: Session, payment_request: PaymentRequest) -> None:
        """端末決済試行の更新日時と変更内容をトランザクションに登録する。

        Args:
            mysql_session: 決済試行を更新するMySQLセッション。
            payment_request: 送信ハッシュまたは決済状態を変更済みの試行。

        Returns:
            なし。
        """
        payment_request.updated_at = datetime.now(JST)
        mysql_session.add(payment_request)
