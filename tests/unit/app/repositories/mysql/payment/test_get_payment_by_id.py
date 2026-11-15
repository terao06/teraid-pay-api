from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentStatus
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
