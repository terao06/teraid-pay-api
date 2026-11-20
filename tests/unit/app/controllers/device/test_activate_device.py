"""端末初回有効化Controllerのトランザクション制御を検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import DeviceActivationCodeInvalidException
from app.core.exceptions.message import DEVICE_ACTIVATION_CODE_INVALID_ERROR, SERVER_ERROR
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.responses.device_activate_response import DeviceActivateResponse


ACTIVATION_CODE = "ABCD-EFGH-JKLM"


class TestActivateDevice:
    """コミットとロールバック、HTTP例外への変換を確認する。"""

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_commits_before_returning_credentials(self, get_mysql_db, service_class) -> None:
        """サービス結果の返却前にトランザクションをコミットする。"""
        request = DeviceActivateRequest(activation_code=ACTIVATION_CODE)
        activation = DeviceActivateResponse(device_uuid="device-uuid", device_credential="credential")
        service = service_class.return_value
        service.activate_device.return_value = activation
        committed = Mock()

        with Session() as session:
            event.listen(session, "after_commit", committed)
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            result = DeviceController().activate_device(request=request)

            committed.assert_called_once_with(session)
            service.activate_device.assert_called_once_with(
                mysql_session=session,
                activation_code=ACTIVATION_CODE,
            )
        assert result == activation

    @pytest.mark.parametrize(
        ("failure", "status_code", "message"),
        [
            (DeviceActivationCodeInvalidException(), 400, DEVICE_ACTIVATION_CODE_INVALID_ERROR),
            (RuntimeError(ACTIVATION_CODE), 500, SERVER_ERROR),
            (HTTPException(status_code=403, detail=ACTIVATION_CODE), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_service_failure(
        self,
        get_mysql_db,
        service_class,
        failure,
        status_code,
        message,
        caplog,
    ) -> None:
        """業務処理の失敗をロールバックし、機密値を記録せずHTTP例外に変換する。"""
        request = DeviceActivateRequest(activation_code=ACTIVATION_CODE)
        service_class.return_value.activate_device.side_effect = failure

        with Session() as session:
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            with patch.object(session, "rollback", wraps=session.rollback) as rollback:
                with pytest.raises(HTTPException) as exc_info:
                    DeviceController().activate_device(request=request)

                rollback.assert_called_once_with()
        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
        assert ACTIVATION_CODE not in caplog.text

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_commit_failure(self, get_mysql_db, service_class, caplog) -> None:
        """コミット失敗時は生成済みの端末認証情報を返さず、500に変換する。"""
        request = DeviceActivateRequest(activation_code=ACTIVATION_CODE)
        activation = DeviceActivateResponse(
            device_uuid="device-uuid",
            device_credential="test-device-credential",
        )
        service_class.return_value.activate_device.return_value = activation
        rolled_back = Mock()
        fail_commit = Mock(side_effect=RuntimeError(activation.device_credential))

        with Session() as session:
            event.listen(session, "before_commit", fail_commit)
            event.listen(session, "after_rollback", rolled_back)
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            with pytest.raises(HTTPException) as exc_info:
                DeviceController().activate_device(request=request)

            rolled_back.assert_called_once_with(session)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {"status": "error", "message": SERVER_ERROR}
        assert activation.device_credential not in caplog.text
