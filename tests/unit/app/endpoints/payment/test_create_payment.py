from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_create_response import PaymentCreateResponse
from app.services.payment_service import JST


class TestCreatePayment:
    """create_payment エンドポイントの単体テスト。"""

    @patch("app.endpoints.payment.PaymentController.create_payment_request")
    def test_create_payment_returns_wrapped_success(
        self,
        mock_create_payment_request,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_create_payment_request.return_value = PaymentCreateResponse(
            payment_request_id=501,
            from_wallet_address="0x1111111111111111111111111111111111111111",
            to_wallet_address="0x2222222222222222222222222222222222222222",
            amount=1500,
            token_symbol="JPYC",
            chain_id=11155111,
            expires_at="2026-04-12 12:10",
        )

        response = client.post(
            "/payment/request",
            json={
                "store_id": 101,
                "user_id": 201,
                "amount": 1500,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": 501,
                "from_wallet_address": "0x1111111111111111111111111111111111111111",
                "to_wallet_address": "0x2222222222222222222222222222222222222222",
                "amount": 1500,
                "token_symbol": "JPYC",
                "chain_id": 11155111,
                "expires_at": "2026-04-12 12:10",
            },
        }
        mock_create_payment_request.assert_called_once()
        request = mock_create_payment_request.call_args.kwargs["request"]
        assert request.store_id == 101
        assert request.user_id == 201
        assert request.amount == 1500

    @patch("app.endpoints.payment.PaymentController.create_payment_request")
    def test_create_payment_returns_http_exception_from_controller(
        self,
        mock_create_payment_request,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_create_payment_request.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "wallet not found",
            },
        )

        response = client.post(
            "/payment/request",
            json={
                "store_id": 101,
                "user_id": 201,
                "amount": 1500,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "wallet not found",
            }
        }

    @pytest.mark.usefixtures("insert_stores", "insert_users", "insert_wallets", "insert_store_wallets", "insert_user_wallets")
    @patch("app.services.payment_service.datetime")
    def test_with_db(
        self,
        mock_datetime,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携時に決済リクエストを作成し、保存内容とレスポンスが一致することを確認する。"""
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)
        mock_datetime.now.return_value = fixed_now

        response = client_with_db.post(
            "/payment/request",
            json={
                "store_id": 101,
                "user_id": 101,
                "amount": 1500,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": 1,
                "from_wallet_address": "0x1111111111111111111111111111111111111111",
                "to_wallet_address": "0x1111111111111111111111111111111111111111",
                "amount": 1500,
                "token_symbol": "JPYC",
                "chain_id": 1,
                "expires_at": "2026-04-12 12:10",
            },
        }

        saved_payment_request = session.query(PaymentRequest).one()
        assert saved_payment_request.payment_request_id == 1
        assert saved_payment_request.store_id == 101
        assert saved_payment_request.user_id == 101
        assert saved_payment_request.store_wallet_address == "0x1111111111111111111111111111111111111111"
        assert saved_payment_request.user_wallet_address == "0x1111111111111111111111111111111111111111"
        assert saved_payment_request.amount == Decimal("1500.000000")
        assert saved_payment_request.token_symbol == "JPYC"
        assert saved_payment_request.chain_id == 1
        assert saved_payment_request.status == PaymentStatus.REQUESTED
        assert saved_payment_request.transaction_hash is None
        assert saved_payment_request.expires_at == (fixed_now + timedelta(minutes=10)).replace(tzinfo=None)
        assert saved_payment_request.created_at is not None
        assert saved_payment_request.updated_at is not None
        assert saved_payment_request.deleted_at is None
