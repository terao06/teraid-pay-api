from unittest.mock import patch

from fastapi import HTTPException

from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse


class TestExecutePayment:
    """execute_payment endpoint tests."""

    @patch("app.endpoints.payment.PaymentController.execute_payment")
    def test_execute_payment_returns_wrapped_success(
        self,
        mock_execute_payment,
        client,
    ) -> None:
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        mock_execute_payment.return_value = PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
        )

        response = client.post(f"/payment/request/{payment_request_id}/execute")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "transaction_hash": transaction_hash,
            },
        }
        mock_execute_payment.assert_called_once()
        call_kwargs = mock_execute_payment.call_args.kwargs
        assert call_kwargs["payment_request_id"] == payment_request_id

    @patch("app.endpoints.payment.PaymentController.execute_payment")
    def test_execute_payment_returns_http_exception_from_controller(
        self,
        mock_execute_payment,
        client,
    ) -> None:
        payment_request_id = 501
        mock_execute_payment.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "payment request not found",
            },
        )

        response = client.post(f"/payment/request/{payment_request_id}/execute")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "payment request not found",
            }
        }
