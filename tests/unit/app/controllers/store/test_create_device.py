"""デバイス登録Controllerのテスト。"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import SERVER_ERROR
from app.models.requests.device_create_request import DeviceCreateRequest
from app.models.responses.device_create_response import DeviceCreateResponse


class TestCreateDevice:
    """StoreControllerのデバイス登録を検証する。"""

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_create_device(self, mock_service_class) -> None:
        """Serviceが返したデバイス登録結果をそのまま返す。"""
        mysql_session = Mock()
        request = DeviceCreateRequest(device_name="レジ端末1")
        expected = DeviceCreateResponse(
            device_id=1,
        )
        mock_service_class.return_value.create_device.return_value = expected

        result = StoreController.create_device.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.create_device.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_maps_unexpected_error_to_500(self, mock_service_class) -> None:
        """想定外例外を500のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.create_device.side_effect = Exception()

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_device.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                request=DeviceCreateRequest(device_name="レジ端末1"),
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }

