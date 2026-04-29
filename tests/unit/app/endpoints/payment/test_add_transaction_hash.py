from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse


class TestAddTransactionHash:
    """add_transaction_hash エンドポイントの単体テスト。"""

    @patch("app.endpoints.payment.PaymentController.add_transaction_hash")
    def test_add_transaction_hash_returns_wrapped_success(
        self,
        mock_add_transaction_hash,
        client,
    ) -> None:
        """controller の結果が success レスポンスラップ付きで返ることを確認する。"""
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        mock_add_transaction_hash.return_value = PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
        )

        response = client.post(
            f"/payment/request/{payment_request_id}/tx",
            json={
                "transaction_hash": transaction_hash,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "transaction_hash": transaction_hash,
            },
        }
        mock_add_transaction_hash.assert_called_once()
        call_kwargs = mock_add_transaction_hash.call_args.kwargs
        assert call_kwargs["payment_request_id"] == payment_request_id
        assert call_kwargs["request"].transaction_hash == transaction_hash

    @patch("app.endpoints.payment.PaymentController.add_transaction_hash")
    def test_add_transaction_hash_returns_http_exception_from_controller(
        self,
        mock_add_transaction_hash,
        client,
    ) -> None:
        """controller の HTTPException がそのまま返ることを確認する。"""
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        mock_add_transaction_hash.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "payment request not found",
            },
        )

        response = client.post(
            f"/payment/request/{payment_request_id}/tx",
            json={
                "transaction_hash": transaction_hash,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "payment request not found",
            }
        }

    @pytest.mark.usefixtures("insert_payment_requests")
    def test_with_db(
        self,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携エンドポイントが対象 payment に transaction_hash を設定することを確認する。"""
        payment_request_id = 401
        transaction_hash = "0xabcdef1234567890"

        response = client_with_db.post(
            f"/payment/request/{payment_request_id}/tx",
            json={
                "transaction_hash": transaction_hash,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "transaction_hash": transaction_hash,
            },
        }

        session.expire_all()
        saved_payment_request = (
            session.query(PaymentRequest)
            .filter(PaymentRequest.payment_request_id == payment_request_id)
            .one()
        )
        assert saved_payment_request.status == PaymentStatus.SUBMITTED
        assert saved_payment_request.transaction_hash == transaction_hash
        assert saved_payment_request.deleted_at is None
