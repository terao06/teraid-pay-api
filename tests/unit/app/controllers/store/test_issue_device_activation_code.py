"""デバイス有効化コード発行Controllerのテスト。"""

from datetime import datetime
from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import (
    DeviceAlreadyActivatedException,
    DeviceNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_ALREADY_ACTIVATED_ERROR,
    DEVICE_NOT_FOUND_ERROR,
    SERVER_ERROR,
)
from app.core.utils.datetime import JST
from app.models.responses.device_activation_code_response import (
    DeviceActivationCodeResponse,
)


class TestIssueDeviceActivationCode:
    """StoreControllerの有効化コード発行を検証する。"""

    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_returns_service_result(self, mock_service_class) -> None:
        """発行対象をServiceへ渡して結果を返す。"""
        mysql_session = Mock()
        expected = DeviceActivationCodeResponse(
            device_id=1,
            activation_code="ABCD-EFGH-JKLM",
            qr_code_image="data:image/png;base64,cG5n",
            activation_expires_at=datetime(2026, 11, 18, 10, 0, tzinfo=JST),
        )
        mock_service_class.return_value.issue_activation_code.return_value = expected

        result = StoreController.issue_device_activation_code.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

        assert result == expected
        mock_service_class.return_value.issue_activation_code.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

    @pytest.mark.parametrize(
        ("side_effect", "status_code", "message"),
        [
            (DeviceNotFoundException(), 404, DEVICE_NOT_FOUND_ERROR),
            (
                DeviceAlreadyActivatedException(),
                409,
                DEVICE_ALREADY_ACTIVATED_ERROR,
            ),
            (Exception(), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.store_controller.StoreDeviceService")
    def test_maps_errors(
        self,
        mock_service_class,
        side_effect,
        status_code,
        message,
    ) -> None:
        """未存在、有効化済み、想定外例外をHTTPエラーへ変換する。"""
        mock_service_class.return_value.issue_activation_code.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            StoreController.issue_device_activation_code.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                device_id=1,
            )

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
