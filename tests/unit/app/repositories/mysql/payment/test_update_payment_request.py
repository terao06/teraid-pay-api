import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.repositories.mysql.payment_repository import PaymentRepository


@pytest.mark.usefixtures("insert_payment_requests")
class TestUpdatePaymentRequest:
    """update_payment_request の単体テスト。"""

    def test_update_payment_request(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = PaymentRepository()
        payment_request = (
            mysql_session.query(PaymentRequest)
            .filter(PaymentRequest.payment_request_id == 401)
            .one()
        )
        before_updated_at = payment_request.updated_at

        payment_request.status = PaymentStatus.SUBMITTED
        payment_request.transaction_hash = (
            "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        )

        result = repository.update_payment_request(mysql_session, payment_request)
        mysql_session.flush()
        mysql_session.expire_all()

        saved_payment_request = (
            mysql_session.query(PaymentRequest)
            .filter(PaymentRequest.payment_request_id == 401)
            .one()
        )

        assert result is payment_request
        assert saved_payment_request.payment_request_id == 401
        assert saved_payment_request.status == PaymentStatus.SUBMITTED
        assert (
            saved_payment_request.transaction_hash
            == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        )
        assert saved_payment_request.updated_at is not None
        assert saved_payment_request.updated_at > before_updated_at
        assert saved_payment_request.deleted_at is None
