from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.repositories.mysql.payment_repository import PaymentRepository

@pytest.mark.usefixtures("insert_payment_requests")
class TestCreatePaymentRequest:
    """create_payment_request の単体テスト。"""

    def test_create_payment_request(
        self,
        mysql_session: Session,
    ) -> None:
        """payment_request を保存し、flush 後に採番済み ID と保存内容を取得できることを検証する。"""
        repository = PaymentRepository()
        payment_request = PaymentRequest(
            store_id=101,
            user_id=102,
            store_wallet_address="0x1111111111111111111111111111111111111111",
            user_wallet_address="0x4444444444444444444444444444444444444444",
            amount=Decimal("1234.560000"),
            token_symbol="JPYC",
            chain_id=11155111,
            status=PaymentStatus.REQUESTED,
            transaction_hash=None,
            expires_at=datetime(2026, 4, 13, 12, 30, 0),
        )

        result = repository.create_payment_request(mysql_session, payment_request)
        mysql_session.expire_all()

        saved_payment_request = (
            mysql_session.query(PaymentRequest)
            .filter(
                PaymentRequest.payment_request_id
                == payment_request.payment_request_id
            )
            .one()
        )

        assert result is payment_request
        assert payment_request.payment_request_id is not None
        assert saved_payment_request.payment_request_id == payment_request.payment_request_id
        assert saved_payment_request.store_id == 101
        assert saved_payment_request.user_id == 102
        assert (
            saved_payment_request.store_wallet_address
            == "0x1111111111111111111111111111111111111111"
        )
        assert (
            saved_payment_request.user_wallet_address
            == "0x4444444444444444444444444444444444444444"
        )
        assert saved_payment_request.amount == Decimal("1234.560000")
        assert saved_payment_request.token_symbol == "JPYC"
        assert saved_payment_request.chain_id == 11155111
        assert saved_payment_request.status == PaymentStatus.REQUESTED
        assert saved_payment_request.transaction_hash is None
        assert saved_payment_request.expires_at == datetime(2026, 4, 13, 12, 30, 0)
        assert saved_payment_request.created_at is not None
        assert saved_payment_request.updated_at is not None
        assert saved_payment_request.deleted_at is None
