"""来店セッション終了のトランザクションとHTTPエラー変換を検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import (
    UnauthorizedException,
    VisitSessionCompletionConflictException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    DEVICE_CHECKOUT_PROCESSING_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
    VISIT_SESSION_UNPAID_ORDERS_ERROR,
)


REQUEST_ARGS = {"device_uuid": "93100100-0000-4000-8000-000000931001", "visit_session_id": 932001}


class TestCompleteVisitSession:
    """セッション終了のコミットとエラー時のロールバックを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_commits_and_returns_closed_visit(self) -> None:
        """Serviceに検証済みの入力と接続を渡し、終了結果をコミットして返す。

        Args:
            なし。

        Returns:
            なし。
        """
        session = Mock(spec=Session, info={})
        with (
            patch("app.middlewares.transaction.get_mysql_db") as get_db,
            patch("app.controllers.device_controller.DeviceService") as service,
        ):
            get_db.return_value.get_session.return_value = nullcontext(session)
            result = DeviceController().complete_visit_session(**REQUEST_ARGS)

        service.return_value.complete_visit_session.assert_called_once_with(mysql_session=session, **REQUEST_ARGS)
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()
        assert result.model_dump() == {"visit_session_id": 932001, "status": "closed"}

    @pytest.mark.parametrize(
        ("error", "status", "message"),
        [
            (UnauthorizedException(), 401, DEVICE_AUTHENTICATION_FAILED_ERROR),
            (VisitSessionNotFoundException(), 404, VISIT_SESSION_NOT_FOUND_ERROR),
            (VisitSessionCompletionConflictException(DEVICE_CHECKOUT_PROCESSING_ERROR), 409,
             DEVICE_CHECKOUT_PROCESSING_ERROR),
            (VisitSessionCompletionConflictException(VISIT_SESSION_UNPAID_ORDERS_ERROR), 409,
             VISIT_SESSION_UNPAID_ORDERS_ERROR),
            (RuntimeError("query failed"), 500, SERVER_ERROR),
            (None, 500, SERVER_ERROR),
        ],
    )
    def test_rolls_back_and_translates_errors(self, error: Exception | None, status: int, message: str) -> None:
        """業務・参照・コミットの失敗を共通のHTTP応答に変換する。

        Args:
            error: Serviceが送出する例外。Noneの場合はコミットで失敗させる。
            status: HTTPステータスの期待値。
            message: エラーメッセージの期待値。

        Returns:
            なし。
        """
        session = Mock(spec=Session, info={})
        if error is None:
            session.commit.side_effect = RuntimeError("commit failed")
        with (
            patch("app.middlewares.transaction.get_mysql_db") as get_db,
            patch("app.controllers.device_controller.DeviceService") as service,
        ):
            get_db.return_value.get_session.return_value = nullcontext(session)
            service.return_value.complete_visit_session.side_effect = error
            with pytest.raises(HTTPException) as failure:
                DeviceController().complete_visit_session(**REQUEST_ARGS)

        assert failure.value.status_code == status
        assert failure.value.detail == {"status": "error", "message": message}
        assert failure.value.headers == ({"WWW-Authenticate": "Bearer"} if status == 401 else None)
        session.rollback.assert_called_once_with()
        assert session.commit.call_count == int(error is None)
