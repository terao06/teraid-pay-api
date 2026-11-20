"""端末アクセストークン発行Controllerのトランザクションを検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import UnauthorizedException
from app.core.exceptions.message import DEVICE_AUTHENTICATION_FAILED_ERROR, SERVER_ERROR
from app.models.requests.device_access_token_request import DeviceAccessTokenRequest
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse


DEVICE_UUID = "81005100-0000-4000-8000-000000000051"
DEVICE_CREDENTIAL = "test-device-access-credential"
ACCESS_TOKEN = "test-access-token"
REQUEST = DeviceAccessTokenRequest(device_uuid=DEVICE_UUID, device_credential=DEVICE_CREDENTIAL)


class TestIssueDeviceAccessToken:
    """コミットとロールバック、HTTP例外への変換を確認する。"""

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_commits_before_returning_token(self, get_mysql_db, service_class) -> None:
        """最終認証日時の更新をコミットしてから発行結果を返す。"""
        token = DeviceAccessTokenResponse(access_token=ACCESS_TOKEN, expires_in=300)
        service = service_class.return_value
        service.issue_device_access_token.return_value = token
        committed = Mock()

        with Session() as session:
            event.listen(session, "after_commit", committed)
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            result = DeviceController().issue_device_access_token(request=REQUEST)

            committed.assert_called_once_with(session)
            service.issue_device_access_token.assert_called_once_with(
                mysql_session=session,
                device_uuid=DEVICE_UUID,
                device_credential=DEVICE_CREDENTIAL,
            )
        assert result == token

    @pytest.mark.parametrize(
        ("failure", "status_code", "message"),
        [
            (UnauthorizedException(), 401, DEVICE_AUTHENTICATION_FAILED_ERROR),
            (RuntimeError(DEVICE_CREDENTIAL), 500, SERVER_ERROR),
            (HTTPException(status_code=403, detail=DEVICE_CREDENTIAL), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_service_failure(
        self, get_mysql_db, service_class, failure, status_code, message, caplog,
    ) -> None:
        """サービス失敗時はロールバックして、機密値を記録せずHTTP例外に変換する。"""
        service_class.return_value.issue_device_access_token.side_effect = failure

        with Session() as session:
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            with patch.object(session, "rollback", wraps=session.rollback) as rollback:
                with pytest.raises(HTTPException) as exc_info:
                    DeviceController().issue_device_access_token(request=REQUEST)

                rollback.assert_called_once_with()
        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
        assert DEVICE_CREDENTIAL not in caplog.text

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_commit_failure(self, get_mysql_db, service_class, caplog) -> None:
        """コミット失敗時は生成済みトークンを返さず、ロールバックして500に変換する。"""
        service_class.return_value.issue_device_access_token.return_value = (
            DeviceAccessTokenResponse(access_token=ACCESS_TOKEN, expires_in=300)
        )
        rolled_back = Mock()
        fail_commit = Mock(side_effect=RuntimeError(ACCESS_TOKEN))

        with Session() as session:
            event.listen(session, "before_commit", fail_commit)
            event.listen(session, "after_rollback", rolled_back)
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            with pytest.raises(HTTPException) as exc_info:
                DeviceController().issue_device_access_token(request=REQUEST)

            rolled_back.assert_called_once_with(session)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {"status": "error", "message": SERVER_ERROR}
        assert ACCESS_TOKEN not in caplog.text
