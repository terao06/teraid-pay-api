"""デバイス更新Controllerのテスト。"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import (
    DeviceActivationStateInvalidException,
    DeviceNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_ACTIVATION_STATE_INVALID_ERROR,
    DEVICE_NOT_FOUND_ERROR,
    SERVER_ERROR,
)
from app.models.requests.device_update_request import DeviceUpdateRequest
from app.models.responses.device_update_response import DeviceUpdateResponse


class TestUpdateDevice:
    """StoreControllerのデバイス更新を検証する。"""

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_returns_service_result(self, mock_service_class) -> None:
        """更新リクエストをServiceへ渡して結果を返す。"""
        mysql_session = Mock()
        request = DeviceUpdateRequest(device_name="変更後")
        expected = DeviceUpdateResponse(device_id=1)
        mock_service_class.return_value.update_device.return_value = expected

        result = StoreController.update_device.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.update_device.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
            request=request,
        )

    @pytest.mark.parametrize(
        ("service_result", "side_effect", "status_code", "message"),
        [
            (None, DeviceNotFoundException(), 404, DEVICE_NOT_FOUND_ERROR),
            (
                None,
                DeviceActivationStateInvalidException(),
                422,
                DEVICE_ACTIVATION_STATE_INVALID_ERROR,
            ),
            (None, Exception(), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_maps_errors(
        self,
        mock_service_class,
        service_result,
        side_effect,
        status_code,
        message,
    ) -> None:
        """未存在、有効化状態不正、想定外例外をHTTPエラーへ変換する。"""
        service = mock_service_class.return_value
        service.update_device.return_value = service_result
        service.update_device.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            StoreController.update_device.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                device_id=1,
                request=DeviceUpdateRequest(device_name="変更後"),
            )

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
