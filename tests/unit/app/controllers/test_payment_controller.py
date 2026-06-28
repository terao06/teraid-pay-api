from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.payment_controller import PaymentController
from app.core.exceptions.custom_exception import (
    FaceEmbeddingNotFoundException,
    FaceNotFoundException,
    InsufficientFundsError,
    PaymentRequestNotFoundException,
    UserNotFoundException,
    WalletNotPermittedException,
    WalletNotFoundException
)
from app.core.exceptions.message import (
    FACE_NOT_REGISTERED_ERROR,
    FACE_NOTE_FOUND_ERROR,
    INSUFFICIENT_FUNDS_ERROR,
    NOT_MATCH_ERROR,
    PAYMENT_ERROR,
    PAYMENT_INFO_NOT_FOUND,
    SERVER_ERROR,
    USER_NOT_FOUND_ERROR,
    WALLET_NOT_PERMITTED_ERROR,
    WALLET_NOT_FOUND_ERROR
)
from app.models.requests.payment_create_from_face_request import PaymentCreateFromFaceRequest
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
            (WalletNotPermittedException("wallet permit is incomplete"), 400, WALLET_NOT_PERMITTED_ERROR),
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
            (InsufficientFundsError("insufficient funds"), 400, INSUFFICIENT_FUNDS_ERROR),
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


class TestCreateAndExecutePaymentFromFace:
    @patch("app.controllers.payment_controller.PaymentService")
    def test_create_and_execute_payment_from_face(self, mock_service_class) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        request = PaymentCreateFromFaceRequest(
            store_id=101,
            content="base64-encoded-image",
            amount=1000,
        )
        user_id = 201
        payment_request_id = 501
        expected = PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash="0xabcdef1234567890",
        )
        mock_service = mock_service_class.return_value
        mock_service.get_user_id_from_face_image.return_value = user_id
        mock_service.create_payment_request.return_value = payment_request_id
        mock_service.execute_payment.return_value = expected

        result = PaymentController.create_and_execute_payment_from_face.__wrapped__.__wrapped__(
            PaymentController(),
            mysql_session=mysql_session,
            postgres_session=postgres_session,
            request=request,
        )

        mock_service.get_user_id_from_face_image.assert_called_once_with(
            mysql_session=mysql_session,
            postgres_session=postgres_session,
            content=request.content,
        )
        mock_service.create_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=request.store_id,
            user_id=user_id,
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
            (FaceNotFoundException("face not found"), 400, FACE_NOTE_FOUND_ERROR),
            (FaceEmbeddingNotFoundException("face not registered"), 404, FACE_NOT_REGISTERED_ERROR),
            (UserNotFoundException("user not found"), 404, USER_NOT_FOUND_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_create_and_execute_payment_from_face_raise_http_exception_from_get_user_id(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        request = PaymentCreateFromFaceRequest(
            store_id=101,
            content="base64-encoded-image",
            amount=1000,
        )
        mock_service = mock_service_class.return_value
        mock_service.get_user_id_from_face_image.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.create_and_execute_payment_from_face.__wrapped__.__wrapped__(
                PaymentController(),
                mysql_session=mysql_session,
                postgres_session=postgres_session,
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
            (WalletNotFoundException("wallet not found"), 404, WALLET_NOT_FOUND_ERROR),
            (ValueError("wallet values mismatch"), 400, NOT_MATCH_ERROR),
            (WalletNotPermittedException("wallet permit is incomplete"), 400, WALLET_NOT_PERMITTED_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_create_and_execute_payment_from_face_raise_http_exception_from_create(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        request = PaymentCreateFromFaceRequest(
            store_id=101,
            content="base64-encoded-image",
            amount=1000,
        )
        mock_service = mock_service_class.return_value
        mock_service.get_user_id_from_face_image.return_value = 201
        mock_service.create_payment_request.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.create_and_execute_payment_from_face.__wrapped__.__wrapped__(
                PaymentController(),
                mysql_session=mysql_session,
                postgres_session=postgres_session,
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
            (InsufficientFundsError("insufficient funds"), 400, INSUFFICIENT_FUNDS_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_create_and_execute_payment_from_face_raise_http_exception_from_execute(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        request = PaymentCreateFromFaceRequest(
            store_id=101,
            content="base64-encoded-image",
            amount=1000,
        )
        payment_request_id = 501
        mock_service = mock_service_class.return_value
        mock_service.get_user_id_from_face_image.return_value = 201
        mock_service.create_payment_request.return_value = payment_request_id
        mock_service.execute_payment.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.create_and_execute_payment_from_face.__wrapped__.__wrapped__(
                PaymentController(),
                mysql_session=mysql_session,
                postgres_session=postgres_session,
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
