from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.payment_controller import PaymentController
from app.core.exceptions.custom_exception import (
    PaymentRequestNotFoundException,
    WalletNotApprovedException,
    WalletNotFoundException
)
from app.core.exceptions.message import (
    NOT_MATCH_ERROR,
    PAYMENT_ERROR,
    PAYMENT_INFO_NOT_FOUND,
    SERVER_ERROR,
    WALLET_NOT_APPROVED_ERROR,
    WALLET_NOT_FOUND_ERROR
)
from app.models.requests.payment_create_request import PaymentCreateRequest
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.models.responses.payment_verify_response import PaymentVerifyResponse


class TestCreateAndExecutePayment:
    @patch("app.controllers.payment_controller.PaymentService")
    def test_create_and_execute_payment(self, mock_service_class) -> None:
        mysql_session = Mock()
        request = PaymentCreateRequest(
            store_id=101,
            user_id=201,
            amount=1000,
        )
        payment_request_id = 501
        expected = PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash="0xabcdef1234567890",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_payment_request.return_value = payment_request_id
        mock_service.execute_payment.return_value = expected

        result = PaymentController.create_and_execute_payment.__wrapped__(
            PaymentController(),
            mysql_session=mysql_session,
            request=request,
        )

        mock_service.create_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=request.store_id,
            user_id=request.user_id,
            amount=request.amount,
        )
        mock_service.execute_payment.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        assert result == expected

    @patch("app.controllers.payment_controller.PaymentService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (WalletNotFoundException("wallet not found"), 404, WALLET_NOT_FOUND_ERROR),
            (ValueError("wallet values mismatch"), 400, NOT_MATCH_ERROR),
            (WalletNotApprovedException("wallet not approved"), 400, WALLET_NOT_APPROVED_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_create_and_execute_payment_raise_http_exception_from_create(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        mysql_session = Mock()
        request = PaymentCreateRequest(
            store_id=101,
            user_id=201,
            amount=1000,
        )
        mock_service = mock_service_class.return_value
        mock_service.create_payment_request.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.create_and_execute_payment.__wrapped__(
                PaymentController(),
                mysql_session=mysql_session,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }

    @patch("app.controllers.payment_controller.PaymentService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (PaymentRequestNotFoundException("payment request not found"), 404, PAYMENT_INFO_NOT_FOUND),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_create_and_execute_payment_raise_http_exception_from_execute(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        mysql_session = Mock()
        request = PaymentCreateRequest(
            store_id=101,
            user_id=201,
            amount=1000,
        )
        payment_request_id = 501
        mock_service = mock_service_class.return_value
        mock_service.create_payment_request.return_value = payment_request_id
        mock_service.execute_payment.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.create_and_execute_payment.__wrapped__(
                PaymentController(),
                mysql_session=mysql_session,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }


class TestVerifyTransactionHash:
    @patch("app.controllers.payment_controller.PaymentService")
    def test_verify_transaction_hash(self, mock_service_class) -> None:
        mysql_session = Mock()
        payment_request_id = 501
        expected = PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status="PAID",
        )
        mock_service = mock_service_class.return_value
        mock_service.verify_transaction_hash.return_value = expected

        result = PaymentController.verify_transaction_hash.__wrapped__(
            PaymentController(),
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_service.verify_transaction_hash.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        assert result == expected

    @patch("app.controllers.payment_controller.PaymentService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (PaymentRequestNotFoundException("payment request not found"), 404, PAYMENT_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_verify_transaction_hash_raise_http_exception(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        mysql_session = Mock()
        payment_request_id = 501
        mock_service = mock_service_class.return_value
        mock_service.verify_transaction_hash.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.verify_transaction_hash.__wrapped__(
                PaymentController(),
                mysql_session=mysql_session,
                payment_request_id=payment_request_id,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }
