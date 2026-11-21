"""来店セッション開始ControllerのHTTP例外変換とトランザクションを検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import UnauthorizedException, VisitSessionConflictException
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_CONFLICT_ERROR,
)
from app.models.requests.visit_session_start_request import VisitSessionStartRequest


DEVICE_UUID = "81006100-0000-4000-8000-000000000061"
REQUEST = VisitSessionStartRequest(start_request_id="start-request")


class TestStartVisitSession:
    """Controllerのコミット、ロールバック、例外変換を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("created", [False, True])
    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_commits_before_returning_session(self, get_mysql_db, service_class, created) -> None:
        """検証済み端末UUIDをサービスに渡し、コミットしてから結果を返す。

        Args:
            get_mysql_db: DB接続のモック。
            service_class: サービスのモック。
            created: サービスが新規作成したかどうか。

        Returns:
            なし。
        """
        service = service_class.return_value
        service.start_visit_session.return_value = (123, created)
        committed = Mock()

        with Session() as session:
            event.listen(session, "after_commit", committed)
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            result, was_created = DeviceController().start_visit_session(device_uuid=DEVICE_UUID, request=REQUEST)

            committed.assert_called_once_with(session)
            service.start_visit_session.assert_called_once_with(
                mysql_session=session,
                device_uuid=DEVICE_UUID,
                start_request_id=REQUEST.start_request_id,
            )
        assert result.visit_session_id == 123
        assert was_created is created

    @pytest.mark.parametrize(
        ("failure", "status_code", "message"),
        [
            (UnauthorizedException(), 401, DEVICE_AUTHENTICATION_FAILED_ERROR),
            (VisitSessionConflictException(), 409, VISIT_SESSION_CONFLICT_ERROR),
            (RuntimeError("database error detail"), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_service_failure(
        self, get_mysql_db, service_class, failure, status_code, message, caplog,
    ) -> None:
        """サービスの失敗をロールバックし、公開用のエラーだけを応答する。

        Args:
            get_mysql_db: DB接続のモック。
            service_class: サービスのモック。
            failure: サービスが送出する例外。
            status_code: 期待するHTTPステータス。
            message: 期待する公開メッセージ。
            caplog: ログ出力を検証するfixture。

        Returns:
            なし。
        """
        service_class.return_value.start_visit_session.side_effect = failure

        with Session() as session:
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)
            with patch.object(session, "rollback", wraps=session.rollback) as rollback:
                with pytest.raises(HTTPException) as exc_info:
                    DeviceController().start_visit_session(device_uuid=DEVICE_UUID, request=REQUEST)

                rollback.assert_called_once_with()

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
        assert "database error detail" not in caplog.text

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_commit_failure(self, get_mysql_db, service_class) -> None:
        """コミットに失敗した場合はロールバックし、成功結果を返さない。

        Args:
            get_mysql_db: DB接続のモック。
            service_class: サービスのモック。

        Returns:
            なし。
        """
        service_class.return_value.start_visit_session.return_value = (123, True)
        rolled_back = Mock()

        with Session() as session:
            event.listen(session, "before_commit", Mock(side_effect=RuntimeError("commit failed")))
            event.listen(session, "after_rollback", rolled_back)
            get_mysql_db.return_value.get_session.return_value = nullcontext(session)

            with pytest.raises(HTTPException) as exc_info:
                DeviceController().start_visit_session(device_uuid=DEVICE_UUID, request=REQUEST)

            rolled_back.assert_called_once_with(session)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {"status": "error", "message": SERVER_ERROR}

    @patch("app.middlewares.transaction.get_mysql_db", side_effect=RuntimeError("unavailable"))
    def test_reports_database_start_failure(self, get_mysql_db) -> None:
        """接続の開始に失敗した場合も共通形式の500を返す。

        Args:
            get_mysql_db: 接続開始時に失敗するDB接続のモック。

        Returns:
            なし。
        """
        with pytest.raises(HTTPException) as exc_info:
            DeviceController().start_visit_session(device_uuid=DEVICE_UUID, request=REQUEST)

        get_mysql_db.assert_called_once_with()
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {"status": "error", "message": SERVER_ERROR}
