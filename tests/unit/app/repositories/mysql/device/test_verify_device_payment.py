"""端末決済結果のDB検索、排他ロック、一括更新を検証する。"""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.repositories.mysql.device_payment_repository import DevicePaymentRepository


def _create_payment(session: Session, *, deleted: bool = False) -> PaymentRequest:
    """照会専用の会計に紐づく未確定の決済試行を登録する。"""
    return DevicePaymentRepository().create_payment_request(session, PaymentRequest(
        checkout_id=914025, store_id=9201, user_id=107,
        store_wallet_address="0x" + "11" * 20, user_wallet_address="0x" + "22" * 20,
        amount=Decimal("100.125"), chain_id=11155111, status=PaymentStatus.REQUESTED,
        expires_at=datetime(2026, 11, 22), deleted_at=datetime(2026, 11, 21) if deleted else None,
    ))


@pytest.mark.usefixtures("insert_face_checkout_payment_data")
class TestVerifyDevicePayment:
    """決済照会の端末・店舗境界と更新時の排他制御を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_filters_device_store_checkout_and_soft_deleted_payment(self, mysql_session) -> None:
        """正しい所属・会計・試行IDで未削除の試行だけを返す。

        Args:
            mysql_session: 実MySQLのテスト用セッション。

        Returns:
            なし。
        """
        repository = DevicePaymentRepository()
        payment = _create_payment(mysql_session)
        deleted = _create_payment(mysql_session, deleted=True)
        result = repository.get_payment_for_result(mysql_session, 911024, 9201, 914025, payment.payment_request_id)
        assert result is not None
        assert result[0] is payment
        assert result[1].visit_session_id == 912024
        for device_id, store_id, checkout_id, payment_id in (
            (911023, 9201, 914025, payment.payment_request_id),
            (911024, 102, 914025, payment.payment_request_id),
            (911024, 9201, 914024, payment.payment_request_id),
            (911024, 9201, 914025, deleted.payment_request_id),
        ):
            assert repository.get_payment_for_result(mysql_session, device_id, store_id, checkout_id, payment_id) is None
        assert repository.get_payment_for_update(mysql_session, 9201, 914025, deleted.payment_request_id) is None

    def test_sender_and_verifier_lock_the_payment_row(self, mysql_engine) -> None:
        """送信後の状態更新と結果確定が同じ決済試行のロックを使う。

        Args:
            mysql_engine: 独立したトランザクションを開くMySQL Engine。

        Returns:
            なし。
        """
        repository = DevicePaymentRepository()
        with Session(mysql_engine) as initial, initial.begin():
            payment_id = _create_payment(initial).payment_request_id
        competing_query = select(PaymentRequest.payment_request_id).where(
            PaymentRequest.payment_request_id == payment_id,
        ).with_for_update(nowait=True)
        with Session(mysql_engine) as locking, Session(mysql_engine) as competing:
            for getter, args in (
                (repository.get_requested_payment, (914025, payment_id)),
                (repository.get_payment_for_update, (9201, 914025, payment_id)),
            ):
                assert getter(locking, *args).payment_request_id == payment_id
                with pytest.raises(OperationalError) as locked:
                    competing.scalar(competing_query)
                assert locked.value.orig.args[0] == 3572
                competing.rollback()
                locking.rollback()
                assert competing.scalar(competing_query) == payment_id
                competing.rollback()

    def test_gets_and_locks_checkout_orders_and_can_update_them_together(self, mysql_engine) -> None:
        """会計明細から対象注文を取得し、排他ロック下で一括更新する。

        Args:
            mysql_engine: 独立したトランザクションを開くMySQL Engine。

        Returns:
            なし。
        """
        repository = DevicePaymentRepository()
        competing_query = (
            select(MenuOrder.menu_order_id)
            .where(MenuOrder.menu_order_id == 913001)
            .with_for_update(nowait=True)
        )
        with Session(mysql_engine) as locking, Session(mysql_engine) as competing:
            orders = repository.get_checkout_orders_for_update(locking, 914001)
            assert {order.menu_order_id for order in orders} == {913001, 913002}
            assert repository.get_checkout_orders_for_update(locking, 914005) == []
            with pytest.raises(OperationalError) as locked:
                competing.scalar(competing_query)
            assert locked.value.orig.args[0] == 3572
            competing.rollback()

            order_ids = [order.menu_order_id for order in orders]
            assert repository.mark_checkout_orders_paid(locking, order_ids) == 2
            locking.expire_all()
            for order_id in order_ids:
                updated = locking.get(MenuOrder, order_id)
                assert updated.status == OrderStatus.PAID
                assert updated.paid_at is not None
            locking.rollback()

            assert competing.scalar(competing_query) == 913001
            for order_id in order_ids:
                assert competing.get(MenuOrder, order_id).paid_at is None

    def test_reads_all_items_of_checkout_orders(self, mysql_session: Session) -> None:
        """会計に未選択の兄弟明細も含めて注文時の数量を取得する。

        Args:
            mysql_session: 実MySQLのテスト用セッション。

        Returns:
            なし。
        """
        repository = DevicePaymentRepository()
        orders = repository.get_checkout_orders_for_update(mysql_session, 914026)
        assert [order.menu_order_id for order in orders] == [913026]
        items = repository.get_order_items(mysql_session, [913026])
        assert {item.menu_order_item_id: item.quantity for item in items} == {915026: 2, 915027: 1}
