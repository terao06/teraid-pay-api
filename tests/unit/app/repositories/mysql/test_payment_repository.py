from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.repositories.mysql.payment_repository import PaymentRepository


@pytest.mark.usefixtures("insert_payment_requests")
class TestGetPaymentById:
    """get_payment_by_id の単体テスト。"""

    @pytest.mark.parametrize(
        ("payment_request_id", "status", "expected_payment"),
        [
            (
                401,
                None,
                {
                    "payment_request_id": 401,
                    "store_id": 101,
                    "user_id": 101,
                    "store_wallet_address": "0x1111111111111111111111111111111111111111",
                    "user_wallet_address": "0x1111111111111111111111111111111111111111",
                    "amount": Decimal("1000.500000"),
                    "token_symbol": "JPYC",
                    "chain_id": 11155111,
                    "status": PaymentStatus.REQUESTED,
                    "transaction_hash": None,
                    "expires_at": "2026-04-13 12:00:00",
                },
            ),
            (
                401,
                PaymentStatus.REQUESTED,
                {
                    "payment_request_id": 401,
                    "store_id": 101,
                    "user_id": 101,
                    "store_wallet_address": "0x1111111111111111111111111111111111111111",
                    "user_wallet_address": "0x1111111111111111111111111111111111111111",
                    "amount": Decimal("1000.500000"),
                    "token_symbol": "JPYC",
                    "chain_id": 11155111,
                    "status": PaymentStatus.REQUESTED,
                    "transaction_hash": None,
                    "expires_at": "2026-04-13 12:00:00",
                },
            ),
            (
                401,
                PaymentStatus.PAID,
                None,
            ),
            (
                402,
                PaymentStatus.PAID,
                {
                    "payment_request_id": 402,
                    "store_id": 104,
                    "user_id": 102,
                    "store_wallet_address": "0x4444444444444444444444444444444444444444",
                    "user_wallet_address": "0x4444444444444444444444444444444444444444",
                    "amount": Decimal("250.000000"),
                    "token_symbol": "JPYC",
                    "chain_id": 11155111,
                    "status": PaymentStatus.PAID,
                    "transaction_hash": (
                        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    ),
                    "expires_at": "2026-04-14 12:00:00",
                },
            ),
            (
                402,
                PaymentStatus.REQUESTED,
                None,
            ),
            (
                999,
                PaymentStatus.REQUESTED,
                None,
            ),
        ],
    )
    def test_get_payment_by_id(
        self,
        mysql_session: Session,
        payment_request_id: int,
        status: PaymentStatus | None,
        expected_payment: dict | None,
    ) -> None:
        """決済リクエスト ID と status で取得し、対象外は None を返すことを確認する。"""
        repository = PaymentRepository()

        result = repository.get_payment_by_id(mysql_session, payment_request_id, status)

        if expected_payment is None:
            assert result is None
            return

        assert result is not None
        assert result.payment_request_id == expected_payment["payment_request_id"]
        assert result.store_id == expected_payment["store_id"]
        assert result.user_id == expected_payment["user_id"]
        assert result.store_wallet_address == expected_payment["store_wallet_address"]
        assert result.user_wallet_address == expected_payment["user_wallet_address"]
        assert result.amount == expected_payment["amount"]
        assert result.token_symbol == expected_payment["token_symbol"]
        assert result.chain_id == expected_payment["chain_id"]
        assert result.status == expected_payment["status"]
        assert result.transaction_hash == expected_payment["transaction_hash"]
        expires_at = result.expires_at.isoformat(sep=" ") if result.expires_at else None
        assert expires_at == expected_payment["expires_at"]


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


@pytest.mark.usefixtures("insert_payment_requests")
class TestUpdatePaymentRequest:
    """update_payment_request の単体テスト。"""

    def test_update_payment_request(
        self,
        mysql_session: Session,
    ) -> None:
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
