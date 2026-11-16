"""デバイス一覧取得Controllerのテスト。"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import SERVER_ERROR
from app.models.responses.device_list_response import (
    DeviceListResponse,
    DevicePaginationResponse,
)


class TestGetDevices:
    """StoreControllerのデバイス一覧取得を検証する。"""

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_returns_service_result(self, mock_service_class) -> None:
        """検索条件をServiceへ渡し、取得結果をそのまま返す。"""
        mysql_session = Mock()
        expected = DeviceListResponse(
            devices=[],
            pagination=DevicePaginationResponse(
                page=1,
                page_size=20,
                total=0,
                total_pages=0,
            ),
        )
        mock_service_class.return_value.get_devices.return_value = expected

        result = StoreController.get_devices.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            device_name="レジ",
            is_active=False,
            page=1,
            page_size=20,
        )

        assert result == expected
        mock_service_class.return_value.get_devices.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_name="レジ",
            is_active=False,
            page=1,
            page_size=20,
        )

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_maps_unexpected_error_to_500(self, mock_service_class) -> None:
        """想定外例外を500のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.get_devices.side_effect = Exception()

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_devices.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
