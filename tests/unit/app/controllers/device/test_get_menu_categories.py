"""カテゴリー一覧Controllerの例外変換とトランザクションを検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import UnauthorizedException, VisitSessionNotFoundException
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
)
from app.models.responses.menu_category_response import DeviceMenuCategoryListResponse


DEVICE_UUID = "81006600-0000-4000-8000-000000000066"
VISIT_SESSION_ID = 820066


def _mock_session(get_mysql_db: Mock) -> Mock:
    """トランザクションが使うMySQLセッションをモックし、DB接続に紐づける。"""
    session = Mock(spec=Session)
    session.info = {}
    get_mysql_db.return_value.get_session.return_value = nullcontext(session)
    return session


class TestGetMenuCategories:
    """端末用カテゴリー取得のトランザクションとHTTP例外を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_returns_categories_after_transaction(self, get_mysql_db, service_class) -> None:
        """認証済み端末と来店セッションIDをServiceに渡し、処理を確定する。

        Args:
            get_mysql_db: MySQL接続のモック。
            service_class: 端末用Serviceのモック。

        Returns:
            なし。
        """
        session = _mock_session(get_mysql_db)
        service = service_class.return_value
        service.get_menu_categories.return_value = DeviceMenuCategoryListResponse(menu_categories=[])

        result = DeviceController().get_menu_categories(device_uuid=DEVICE_UUID, visit_session_id=VISIT_SESSION_ID)

        assert result is service.get_menu_categories.return_value
        service.get_menu_categories.assert_called_once_with(
            mysql_session=session,
            device_uuid=DEVICE_UUID,
            visit_session_id=VISIT_SESSION_ID,
        )
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    @pytest.mark.parametrize(
        ("error", "status", "message", "headers"),
        [
            (UnauthorizedException, 401, DEVICE_AUTHENTICATION_FAILED_ERROR, {"WWW-Authenticate": "Bearer"}),
            (VisitSessionNotFoundException, 404, VISIT_SESSION_NOT_FOUND_ERROR, None),
            (RuntimeError, 500, SERVER_ERROR, None),
        ],
    )
    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_and_maps_service_errors(self, get_mysql_db, service_class, error, status, message, headers) -> None:
        """取得失敗を共通のHTTPエラーへ変換し、トランザクションを中断する。

        Args:
            get_mysql_db: MySQL接続のモック。
            service_class: 端末用Serviceのモック。
            error: Serviceで発生させる例外。
            status: 期待するHTTPステータス。
            message: 期待するエラーメッセージ。
            headers: エラー時の期待するHTTPヘッダー。

        Returns:
            なし。
        """
        session = _mock_session(get_mysql_db)
        service_class.return_value.get_menu_categories.side_effect = error

        with pytest.raises(HTTPException) as result:
            DeviceController().get_menu_categories(device_uuid=DEVICE_UUID, visit_session_id=VISIT_SESSION_ID)

        assert result.value.status_code == status
        assert result.value.detail == {"status": "error", "message": message}
        assert result.value.headers == headers
        session.commit.assert_not_called()
        session.rollback.assert_called_once_with()

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_reports_transaction_completion_failure(self, get_mysql_db, service_class, caplog) -> None:
        """トランザクション確定失敗ではDBの詳細を公開せず500を返す。

        Args:
            get_mysql_db: MySQL接続のモック。
            service_class: 端末用Serviceのモック。
            caplog: ログ出力を検証するfixture。

        Returns:
            なし。
        """
        session = _mock_session(get_mysql_db)
        session.commit.side_effect = RuntimeError("transaction failure details")
        service_class.return_value.get_menu_categories.return_value = DeviceMenuCategoryListResponse(menu_categories=[])

        with pytest.raises(HTTPException) as result:
            DeviceController().get_menu_categories(device_uuid=DEVICE_UUID, visit_session_id=VISIT_SESSION_ID)

        assert result.value.status_code == 500
        assert result.value.detail == {"status": "error", "message": SERVER_ERROR}
        session.rollback.assert_called_once_with()
        assert "transaction failure details" not in caplog.text
