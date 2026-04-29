from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.payment_controller import PaymentController
from app.core.exceptions.custom_exception import PaymentRequestNotFoundException, WalletNotFoundException
from app.core.exceptions.message import NOT_MATCH_ERROR, PAYMENT_ERROR, PAYMENT_INFO_NOT_FOUND, SERVER_ERROR, WALLET_NOT_FOUND_ERROR
from app.models.requests.payment_create_request import PaymentCreateRequest
from app.models.requests.payment_transaction_hash_request import PaymentTransactionHashRequest
from app.models.responses.payment_create_response import PaymentCreateResponse
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.models.responses.payment_verify_response import PaymentVerifyResponse


class TestCreatePaymentRequest:
    """PaymentController.create_payment_request の単体テスト。"""

    @patch("app.controllers.payment_controller.PaymentService")
    def test_create_payment_request(self, mock_service_class) -> None:
        """service の戻り値をそのまま返し、引数を正しく引き渡すことを確認する。"""

        session = Mock()
        request = PaymentCreateRequest(
            store_id=101,
            user_id=201,
            amount=1000,
        )
        expected = PaymentCreateResponse(
            payment_request_id=501,
            from_wallet_address="0x1111111111111111111111111111111111111111",
            to_wallet_address="0x2222222222222222222222222222222222222222",
            amount=request.amount,
            token_symbol="JPYC",
            chain_id=11155111,
            expires_at="2026-04-12 12:10",
        )
        mock_service = mock_service_class.return_value
        mock_service.create_payment_request.return_value = expected

        result = PaymentController.create_payment_request.__wrapped__(
            PaymentController(),
            session=session,
            request=request,
        )

        mock_service.create_payment_request.assert_called_once_with(
            session=session,
            store_id=request.store_id,
            user_id=request.user_id,
            amount=request.amount,
        )
        assert result == expected

    @patch("app.controllers.payment_controller.PaymentService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (WalletNotFoundException("wallet not found"), 404, WALLET_NOT_FOUND_ERROR),
            (ValueError("wallet values mismatch"), 400, NOT_MATCH_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_create_payment_request_raise_http_exception(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        """各例外が期待する HTTPException に変換されることを確認する。"""

        session = Mock()
        request = PaymentCreateRequest(
            store_id=101,
            user_id=201,
            amount=1000,
        )
        mock_service = mock_service_class.return_value
        mock_service.create_payment_request.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.create_payment_request.__wrapped__(
                PaymentController(),
                session=session,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }


class TestAddTransactionHash:
    """PaymentController.add_transaction_hash の単体テスト。"""

    @patch("app.controllers.payment_controller.PaymentService")
    def test_add_transaction_hash(self, mock_service_class) -> None:
        """サービスの戻り値を返し、リクエスト値をサービスへ渡すことを確認する。"""

        session = Mock()
        payment_request_id = 501
        request = PaymentTransactionHashRequest(
            payment_request_id=999,
            transaction_hash="0xabcdef1234567890",
        )
        expected = PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash=request.transaction_hash,
        )
        mock_service = mock_service_class.return_value
        mock_service.add_transaction_hash.return_value = expected

        result = PaymentController.add_transaction_hash.__wrapped__(
            PaymentController(),
            session=session,
            payment_request_id=payment_request_id,
            request=request,
        )

        mock_service.add_transaction_hash.assert_called_once_with(
            session=session,
            payment_request_id=payment_request_id,
            transaction_hash=request.transaction_hash,
        )
        assert result == expected

    @patch("app.controllers.payment_controller.PaymentService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (PaymentRequestNotFoundException("payment request not found"), 404, PAYMENT_INFO_NOT_FOUND),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_add_transaction_hash_raise_http_exception(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        """サービス例外が HTTPException レスポンスに変換されることを確認する。"""

        session = Mock()
        payment_request_id = 501
        request = PaymentTransactionHashRequest(
            payment_request_id=999,
            transaction_hash="0xabcdef1234567890",
        )
        mock_service = mock_service_class.return_value
        mock_service.add_transaction_hash.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.add_transaction_hash.__wrapped__(
                PaymentController(),
                session=session,
                payment_request_id=payment_request_id,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }


class TestVerifyTransactionHash:
    """PaymentController.verify_transaction_hash の単体テスト。"""

    @patch("app.controllers.payment_controller.PaymentService")
    def test_verify_transaction_hash(self, mock_service_class) -> None:
        """サービスの戻り値を返し、payment_request_id をサービスへ渡すことを確認する。"""

        session = Mock()
        payment_request_id = 501
        expected = PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status="PAID",
        )
        mock_service = mock_service_class.return_value
        mock_service.verify_transaction_hash.return_value = expected

        result = PaymentController.verify_transaction_hash.__wrapped__(
            PaymentController(),
            session=session,
            payment_request_id=payment_request_id,
        )

        mock_service.verify_transaction_hash.assert_called_once_with(
            session=session,
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
        """サービス例外が HTTPException レスポンスに変換されることを確認する。"""

        session = Mock()
        payment_request_id = 501
        mock_service = mock_service_class.return_value
        mock_service.verify_transaction_hash.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            PaymentController.verify_transaction_hash.__wrapped__(
                PaymentController(),
                session=session,
                payment_request_id=payment_request_id,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }
