"""端末向け決済結果確認コントローラーの応答と例外変換を検証する。"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.controllers.device_payment_controller import DevicePaymentController
from app.core.exceptions.custom_exception import PaymentRequestNotFoundException, UnauthorizedException
from app.helpers.device_payment_chain_helper import DevicePaymentRpcUnavailable
from app.models.mysql.payment_request import PaymentStatus
from app.models.mysql.visit_session import VisitSessionStatus
from app.models.responses.device_payment_result_response import DevicePaymentResultResponse

_SERVICE = "app.controllers.device_payment_controller.DevicePaymentResultService.verify_payment"


class TestVerifyDevicePayment:
    """決済状態とエラーをHTTP応答へ変換する責務を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_returns_service_result(self) -> None:
        """決済サービスの結果、来店セッション状態と未払い有無をそのまま返す。

        Args:
            なし。

        Returns:
            なし。
        """
        result = DevicePaymentResultResponse(
            payment_request_id=8, status=PaymentStatus.PAID, visit_session_status=VisitSessionStatus.ACTIVE,
            has_unpaid_items=True,
        )
        with patch(_SERVICE, return_value=result) as verify:
            assert DevicePaymentController().verify_payment("device-id", 3, 8) == result
        verify.assert_called_once_with("device-id", 3, 8)

    @pytest.mark.parametrize(("error", "status_code"), [
        (UnauthorizedException(), 401),
        (PaymentRequestNotFoundException(), 404),
        (DevicePaymentRpcUnavailable(), 503),
        (RuntimeError(), 500),
    ])
    def test_maps_service_error(self, error: Exception, status_code: int) -> None:
        """認証失敗、対象なし、RPC障害、内部エラーを区別する。

        Args:
            error: サービスで発生する例外。
            status_code: 期待されるHTTPステータス。

        Returns:
            なし。
        """
        with patch(_SERVICE, side_effect=error), pytest.raises(HTTPException) as captured:
            DevicePaymentController().verify_payment("device-id", 3, 8)
        assert captured.value.status_code == status_code
        assert captured.value.detail["status"] == "error"
        if status_code == 401:
            assert captured.value.headers == {"WWW-Authenticate": "Bearer"}
