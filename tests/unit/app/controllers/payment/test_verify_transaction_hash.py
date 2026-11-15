from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.payment_controller import PaymentController
from app.core.exceptions.custom_exception import (
    PaymentRequestNotFoundException,
)
from app.core.exceptions.message import (
    PAYMENT_ERROR,
    SERVER_ERROR,
)
from app.models.responses.payment_verify_response import PaymentVerifyResponse


class TestVerifyTransactionHash:
    """verify_transaction_hash の動作を検証する。"""

    @patch("app.controllers.payment_controller.PaymentService")
    def test_verify_transaction_hash(self, mock_service_class) -> None:
        """正常系の処理結果を検証する。"""
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
        """例外・エラー条件での動作を検証する。"""
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
