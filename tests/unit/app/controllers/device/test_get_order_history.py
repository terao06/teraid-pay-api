"""注文履歴取得の例外変換とトランザクションを検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import UnauthorizedException, VisitSessionNotFoundException
from app.core.exceptions.message import DEVICE_AUTHENTICATION_FAILED_ERROR, SERVER_ERROR, VISIT_SESSION_NOT_FOUND_ERROR
from app.models.responses.device_order_history_response import DeviceOrderHistoryResponse


DEVICE_UUID = "89100100-0000-4000-8000-000000891001"
VISIT_ID = 892001


@pytest.fixture()
def order_history_dependencies():
    """注文履歴用のMySQLセッションとサービスを差し替える。

    Args:
        なし。

    Yields:
        トランザクションのセッションと注文履歴取得モック。
    """
    session = Mock(spec=Session)
    session.info = {}
    with (
        patch("app.middlewares.transaction.get_mysql_db") as mysql,
        patch("app.controllers.device_controller.DeviceOrderService") as service,
    ):
        mysql.return_value.get_session.return_value = nullcontext(session)
        yield session, service.return_value.get_order_history


class TestGetOrderHistory:
    """コントローラーの応答とセッション管理を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_returns_history_after_commit(self, order_history_dependencies) -> None:
        """読み取りに成功するとコミットしてサービスの結果を返す。

        Args:
            order_history_dependencies: セッションとサービスのモック。

        Returns:
            なし。
        """
        session, get_order_history = order_history_dependencies
        expected = DeviceOrderHistoryResponse(orders=[])
        get_order_history.return_value = expected

        result = DeviceController().get_order_history(device_uuid=DEVICE_UUID, visit_session_id=VISIT_ID)

        assert result == expected
        get_order_history.assert_called_once_with(session, DEVICE_UUID, VISIT_ID)
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    @pytest.mark.parametrize(("error", "status", "message", "headers"), [
        (UnauthorizedException(), 401, DEVICE_AUTHENTICATION_FAILED_ERROR, {"WWW-Authenticate": "Bearer"}),
        (VisitSessionNotFoundException(), 404, VISIT_SESSION_NOT_FOUND_ERROR, None),
        (RuntimeError("read failure"), 500, SERVER_ERROR, None),
    ])
    def test_rolls_back_and_translates_errors(self, order_history_dependencies, error, status, message, headers) -> None:
        """認証・セッション・読み取りエラーを変換し、ロールバックする。

        Args:
            order_history_dependencies: セッションとサービスのモック。
            error: サービスが送出する例外。
            status: 期待するHTTPステータス。
            message: 期待する公開エラーメッセージ。
            headers: 期待する公開レスポンスヘッダー。

        Returns:
            なし。
        """
        session, get_order_history = order_history_dependencies
        get_order_history.side_effect = error

        with pytest.raises(HTTPException) as result:
            DeviceController().get_order_history(device_uuid=DEVICE_UUID, visit_session_id=VISIT_ID)

        assert result.value.status_code == status
        assert result.value.detail["message"] == message
        assert result.value.headers == headers
        session.commit.assert_not_called()
        session.rollback.assert_called_once_with()

    def test_returns_server_error_when_commit_fails(self, order_history_dependencies) -> None:
        """読み取り後のコミットが失敗したらロールバックし、500を返す。

        Args:
            order_history_dependencies: セッションとサービスのモック。

        Returns:
            なし。
        """
        session, get_order_history = order_history_dependencies
        get_order_history.return_value = DeviceOrderHistoryResponse(orders=[])
        session.commit.side_effect = RuntimeError("commit failure")

        with pytest.raises(HTTPException) as result:
            DeviceController().get_order_history(device_uuid=DEVICE_UUID, visit_session_id=VISIT_ID)

        assert result.value.status_code == 500
        assert result.value.detail["message"] == SERVER_ERROR
        session.rollback.assert_called_once_with()
