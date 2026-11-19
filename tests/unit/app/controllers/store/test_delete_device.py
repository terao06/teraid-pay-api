"""デバイス削除Controllerの例外変換を確認する。"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import DeviceNotFoundException
from app.core.exceptions.message import DEVICE_NOT_FOUND_ERROR, SERVER_ERROR


@pytest.mark.parametrize(
    ("error", "status_code", "message"),
    [
        (DeviceNotFoundException(), 404, DEVICE_NOT_FOUND_ERROR),
        (RuntimeError(), 500, SERVER_ERROR),
    ],
)
@patch("app.controllers.store_controller.StoreDeviceService")
def test_delete_device_maps_errors(service_class, error, status_code, message) -> None:
    """対象未存在と想定外の失敗を対応するHTTPエラーへ変換する。"""
    service_class.return_value.delete_device.side_effect = error

    with pytest.raises(HTTPException) as exc_info:
        StoreController.delete_device.__wrapped__(
            StoreController(), mysql_session=Mock(), store_id=101, device_id=1
        )

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == {"status": "error", "message": message}
