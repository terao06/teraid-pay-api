"""端末顔認証決済開始のコントローラーとHTTPエラー変換を検証する。"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.device_payment_controller import DevicePaymentController
from app.core.exceptions.custom_exception import (
    DeviceCheckoutConflictException,
    DeviceCheckoutNotFoundException,
    FaceEmbeddingNotFoundException,
    FaceNotFoundException,
    InsufficientFundsError,
    SameFaceFoundException,
    UnauthorizedException,
    WalletMismatchException,
    WalletNotFoundException,
    WalletNotPermittedException,
)
from app.models.responses.device_face_payment_response import DeviceFacePaymentResponse


class TestStartFacePayment:
    """サービスの結果と業務エラーをHTTP応答に変換することを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("status, payment_status", [(200, "paid"), (201, "submitted"), (202, "requested")])
    def test_returns_service_result(self, status, payment_status) -> None:
        """サービスの成功結果とHTTPステータスを引き継ぐ。

        Args:
            status: HTTPステータス。
            payment_status: 決済試行の状態。

        Returns:
            なし。
        """
        result = DeviceFacePaymentResponse(payment_request_id=12, status=payment_status)
        with patch("app.controllers.device_payment_controller.DevicePaymentService.start_face_payment") as start:
            start.return_value = result, status
            assert DevicePaymentController().start_face_payment("device", 1, "key", Mock(content="image")) == (result, status)
        start.assert_called_once_with(device_uuid="device", checkout_id=1, idempotency_key="key", content="image")

    @pytest.mark.parametrize("error, status", [
        (UnauthorizedException(), 401),
        (DeviceCheckoutNotFoundException(), 404),
        (DeviceCheckoutConflictException("会計内容が変更されました。"), 409),
        (FaceEmbeddingNotFoundException(), 404),
        (FaceNotFoundException(), 400),
        (SameFaceFoundException(), 400),
        (InsufficientFundsError(), 400),
        (WalletNotFoundException(), 404),
        (WalletMismatchException(), 400),
        (WalletNotPermittedException(), 400),
        (RuntimeError("internal details"), 500),
    ])
    def test_maps_service_errors(self, error, status) -> None:
        """業務エラーを対応するHTTPステータスと共通形式で返す。

        Args:
            error: サービスから送出される例外。
            status: 期待するHTTPステータス。

        Returns:
            なし。
        """
        with (
            patch("app.controllers.device_payment_controller.DevicePaymentService.start_face_payment", side_effect=error),
            pytest.raises(HTTPException) as failure,
        ):
            DevicePaymentController().start_face_payment("device", 1, "key", Mock(content="image"))
        assert failure.value.status_code == status
        assert failure.value.detail["status"] == "error"
        if status == 401:
            assert failure.value.headers == {"WWW-Authenticate": "Bearer"}
        if status == 500:
            assert "internal details" not in str(failure.value.detail)
