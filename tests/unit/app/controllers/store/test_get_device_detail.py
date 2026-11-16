"""デバイス詳細取得Controllerのテスト。"""

from datetime import datetime
from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import DeviceNotFoundException
from app.core.exceptions.message import DEVICE_NOT_FOUND_ERROR, SERVER_ERROR
from app.core.utils.datetime import JST
from app.models.responses.device_detail_response import DeviceDetailResponse


class TestGetDeviceDetail:
    """StoreControllerのデバイス詳細取得を検証する。"""

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_returns_service_result(self, mock_service_class) -> None:
        """Serviceのデバイス詳細取得結果をそのまま返す。"""
        mysql_session = Mock()
        expected = DeviceDetailResponse(
            device_id=1,
            device_name="レジ端末1",
            is_active=False,
            activated_at=None,
            last_authenticated_at=None,
            created_at=datetime(2026, 11, 16, 10, 0, tzinfo=JST),
            updated_at=datetime(2026, 11, 16, 10, 0, tzinfo=JST),
        )
        mock_service_class.return_value.get_device_detail.return_value = expected

        result = StoreController.get_device_detail.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

        assert result == expected
        mock_service_class.return_value.get_device_detail.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_returns_404_when_device_does_not_exist(self, mock_service_class) -> None:
        """ServiceがNoneを返した場合は404へ変換する。"""
        mock_service_class.return_value.get_device_detail.side_effect = (
            DeviceNotFoundException()
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_device_detail.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                device_id=999,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": DEVICE_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_maps_unexpected_error_to_500(self, mock_service_class) -> None:
        """想定外例外を500のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.get_device_detail.side_effect = Exception()

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_device_detail.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                device_id=1,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
