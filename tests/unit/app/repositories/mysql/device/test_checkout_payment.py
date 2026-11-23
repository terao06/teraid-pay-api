"""顔認証決済開始が使う会計、対象明細と試行のDBクエリを検証する。"""

from datetime import datetime
from decimal import Decimal
from hashlib import sha256

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.mysql.menu_checkout import MenuCheckout
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.repositories.mysql.device_payment_repository import DevicePaymentRepository


@pytest.mark.usefixtures("insert_face_checkout_payment_data")
class TestCheckoutPayment:
    """会計・明細の参照条件、排他ロック、試行の一意性を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_filters_owned_checkout_and_unpaid_order_items(self, mysql_session: Session) -> None:
        """他端末の会計、別店舗・別セッション・削除済み・取り消し済みの注文を除外する。

        Args:
            mysql_session: 実MySQLセッション。

        Returns:
            なし。
        """
        repository = DevicePaymentRepository()
        assert repository.get_owned_checkout(mysql_session, 914001, 911004) is None
        checkout, visit = repository.get_owned_checkout(mysql_session, 914001, 911001)
        assert (checkout.checkout_id, visit.visit_session_id) == (914001, 912001)
        snapshot = repository.get_checkout_items(mysql_session, checkout.checkout_id)
        assert {(row.menu_order_item_id, row.quantity, row.line_amount) for row in snapshot} == {
            (915001, 1, Decimal("1200.125000")),
            (915002, 1, Decimal("300.250000")),
        }
        assert repository.get_checkout_items(mysql_session, 914013) == []
        assert set(repository.get_unpaid_order_items(mysql_session, 9201, 912001)) == {
            (915001, 1, "JPYC"), (915002, 1, "JPYC"),
        }
        assert set(repository.get_unpaid_order_items(mysql_session, 102, 912001)) == {(915007, 1, "JPYC")}
        assert set(repository.get_unpaid_order_items(mysql_session, 9201, 912006)) == {(915011, 1, "JPYC")}

    def test_locks_checkout_until_transaction_ends(self, mysql_engine) -> None:
        """会計行を別トランザクションからのロック取得が失敗する状態にする。

        Args:
            mysql_engine: 独立したMySQLセッションを作成するEngine。

        Returns:
            なし。
        """
        competing_query = (
            select(MenuCheckout.checkout_id).where(MenuCheckout.checkout_id == 914004).with_for_update(nowait=True)
        )
        with Session(mysql_engine) as locking, Session(mysql_engine) as competing:
            checkout = DevicePaymentRepository().get_checkout_for_update(locking, 914004, 912004)
            assert checkout.checkout_id == 914004
            with pytest.raises(OperationalError) as failure:
                competing.scalar(competing_query)
            assert failure.value.orig.args[0] == 3572
            competing.rollback()
            locking.rollback()
            assert competing.scalar(competing_query) == 914004

    def test_returns_exact_key_before_processing_attempt_and_enforces_unique_key(self, mysql_session) -> None:
        """同じキーを優先し、別キーでは処理中の試行と会計の範囲を守る。

        Args:
            mysql_session: 変更をコミットせずに検証する実MySQLセッション。

        Returns:
            なし。
        """
        repository = DevicePaymentRepository()
        failed_key = sha256(b"Failed").digest()
        pending_key = sha256(b"failed").digest()
        fields = {
            "checkout_id": 914004, "store_id": 9201, "user_id": 107,
            "store_wallet_address": "0x1111111111111111111111111111111111111111",
            "user_wallet_address": "0x6666666666666666666666666666666666666666",
            "amount": Decimal("300"), "chain_id": 11155111,
            "expires_at": datetime(2026, 11, 22),
        }
        failed = repository.create_payment_request(
            mysql_session, PaymentRequest(**fields, idempotency_key_hash=failed_key, status=PaymentStatus.ERROR)
        )
        pending = repository.create_payment_request(
            mysql_session, PaymentRequest(**fields, idempotency_key_hash=pending_key, status=PaymentStatus.REQUESTED)
        )
        assert repository.get_checkout_payment(mysql_session, 914004, failed_key, include_processing=True) is failed
        unknown_key = sha256(b"other").digest()
        assert repository.get_checkout_payment(mysql_session, 914004, unknown_key, include_processing=True) is pending
        assert repository.get_checkout_payment(mysql_session, 914004, unknown_key, include_processing=False) is None
        assert repository.get_checkout_payment(mysql_session, 914005, pending_key, include_processing=False) is None
        assert repository.get_requested_payment(mysql_session, 914004, pending.payment_request_id) is pending
        assert repository.get_requested_payment(mysql_session, 914005, pending.payment_request_id) is None
        assert repository.get_requested_payment(mysql_session, 914004, failed.payment_request_id) is None
        with pytest.raises(IntegrityError), mysql_session.begin_nested():
            repository.create_payment_request(mysql_session, PaymentRequest(**fields, idempotency_key_hash=pending_key))
