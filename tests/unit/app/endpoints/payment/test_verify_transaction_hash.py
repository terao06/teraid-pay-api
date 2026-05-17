from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session
from web3.exceptions import TransactionNotFound

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_verify_response import PaymentVerifyResponse


class TestVerifyTransactionHash:
    """verify_transaction_hash エンドポイントの単体テスト。"""

    @patch("app.endpoints.payment.PaymentController.verify_transaction_hash")
    def test_verify_transaction_hash_returns_wrapped_success(
        self,
        mock_verify_transaction_hash,
        client,
    ) -> None:
        """controller の結果が success レスポンスラップ付きで返ることを確認する。"""
        payment_request_id = 501
        mock_verify_transaction_hash.return_value = PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.PAID.value,
        )

        response = client.post(f"/payment/request/{payment_request_id}/verify")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "status": PaymentStatus.PAID.value,
            },
        }
        mock_verify_transaction_hash.assert_called_once_with(
            payment_request_id=payment_request_id,
        )

    @patch("app.endpoints.payment.PaymentController.verify_transaction_hash")
    def test_verify_transaction_hash_returns_http_exception_from_controller(
        self,
        mock_verify_transaction_hash,
        client,
    ) -> None:
        """controller の HTTPException がそのまま返ることを確認する。"""
        payment_request_id = 501
        mock_verify_transaction_hash.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "payment verify error",
            },
        )

        response = client.post(f"/payment/request/{payment_request_id}/verify")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "payment verify error",
            }
        }

    @pytest.mark.usefixtures("insert_payment_requests")
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    def test_with_db(
        self,
        mock_http_provider_class,
        mock_web3_class,
        client_with_db,
        mysql_session: Session,
    ) -> None:
        """DB 連携エンドポイントが receipt 未取得時に payment status を CONFIRMING に更新することを確認する。"""
        payment_request_id = 402
        transaction_hash = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.return_value = None

        response = client_with_db.post(f"/payment/request/{payment_request_id}/verify")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "status": PaymentStatus.CONFIRMING.value,
            },
        }
        mock_http_provider_class.assert_called_once_with("https://polygon-rpc.com")
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()

        mysql_session.expire_all()
        saved_payment_request = (
            mysql_session.query(PaymentRequest)
            .filter(PaymentRequest.payment_request_id == payment_request_id)
            .one()
        )
        assert saved_payment_request.status == PaymentStatus.CONFIRMING
        assert saved_payment_request.transaction_hash == transaction_hash
        assert saved_payment_request.deleted_at is None

    @pytest.mark.usefixtures("insert_payment_requests")
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    def test_with_db_returns_confirming_when_transaction_not_found(
        self,
        mock_http_provider_class,
        mock_web3_class,
        client_with_db,
        mysql_session: Session,
    ) -> None:
        """RPC で transaction が未検出の場合も 500 ではなく CONFIRMING を返すことを確認する。"""
        payment_request_id = 402
        transaction_hash = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.side_effect = TransactionNotFound(
            f"Transaction with hash: {transaction_hash} not found."
        )

        response = client_with_db.post(f"/payment/request/{payment_request_id}/verify")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "status": PaymentStatus.CONFIRMING.value,
            },
        }
        mock_http_provider_class.assert_called_once_with("https://polygon-rpc.com")
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()

        mysql_session.expire_all()
        saved_payment_request = (
            mysql_session.query(PaymentRequest)
            .filter(PaymentRequest.payment_request_id == payment_request_id)
            .one()
        )
        assert saved_payment_request.status == PaymentStatus.CONFIRMING
        assert saved_payment_request.transaction_hash == transaction_hash
        assert saved_payment_request.deleted_at is None
