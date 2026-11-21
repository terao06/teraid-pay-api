"""カテゴリー別メニュー取得Controllerのトランザクションと例外変換を検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import (
    MenuCategoryNotFoundException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    MENU_CATEGORY_NOT_FOUND_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
)
from app.models.responses.device_menu_item_list_response import DeviceMenuItemListResponse


REQUEST_ARGS = {
    "device_uuid": "81006600-0000-4000-8000-000000000066",
    "visit_session_id": 820066,
    "menu_category_id": 830012,
}


def _mock_session(get_mysql_db: Mock) -> Mock:
    """トランザクションにモックのMySQLセッションを渡す。"""
    session = Mock(spec=Session)
    session.info = {}
    get_mysql_db.return_value.get_session.return_value = nullcontext(session)
    return session


class TestGetMenuItemsByCategory:
    """カテゴリー別メニューのController処理を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_returns_menu_after_commit(self, get_mysql_db, service_class) -> None:
        """Serviceに認証済み端末と両IDを渡し、取得後に処理を確定する。

        Args:
            get_mysql_db: DB接続のモック。
            service_class: 端末Serviceのモック。

        Returns:
            なし。
        """
        session = _mock_session(get_mysql_db)
        get_items = service_class.return_value.get_menu_items_by_category
        get_items.return_value = DeviceMenuItemListResponse(menu_items=[])

        result = DeviceController().get_menu_items_by_category(**REQUEST_ARGS)

        assert result is get_items.return_value
        get_items.assert_called_once_with(mysql_session=session, **REQUEST_ARGS)
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    @pytest.mark.parametrize(
        ("error", "status", "message", "headers"),
        [
            (UnauthorizedException, 401, DEVICE_AUTHENTICATION_FAILED_ERROR, {"WWW-Authenticate": "Bearer"}),
            (VisitSessionNotFoundException, 404, VISIT_SESSION_NOT_FOUND_ERROR, None),
            (MenuCategoryNotFoundException, 404, MENU_CATEGORY_NOT_FOUND_ERROR, None),
            (RuntimeError, 500, SERVER_ERROR, None),
        ],
    )
    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_translates_errors_and_rolls_back(self, get_mysql_db, service_class, error, status, message, headers) -> None:
        """Serviceの例外をHTTPエラーにしてロールバックする。

        Args:
            get_mysql_db: DB接続のモック。
            service_class: 端末Serviceのモック。
            error: Serviceが送出する例外。
            status: 想定するHTTPステータス。
            message: 想定するエラーメッセージ。
            headers: 想定するレスポンスヘッダー。

        Returns:
            なし。
        """
        session = _mock_session(get_mysql_db)
        service_class.return_value.get_menu_items_by_category.side_effect = error

        with pytest.raises(HTTPException) as exc_info:
            DeviceController().get_menu_items_by_category(**REQUEST_ARGS)

        assert exc_info.value.status_code == status
        assert exc_info.value.detail == {"status": "error", "message": message}
        assert exc_info.value.headers == headers
        session.commit.assert_not_called()
        session.rollback.assert_called_once_with()

    @patch("app.controllers.device_controller.DeviceService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_returns_server_error_when_commit_fails(self, get_mysql_db, service_class) -> None:
        """トランザクションの確定に失敗した場合は500を返す。

        Args:
            get_mysql_db: DB接続のモック。
            service_class: 端末Serviceのモック。

        Returns:
            なし。
        """
        session = _mock_session(get_mysql_db)
        session.commit.side_effect = RuntimeError("commit failed")
        service_class.return_value.get_menu_items_by_category.return_value = DeviceMenuItemListResponse(menu_items=[])

        with pytest.raises(HTTPException) as exc_info:
            DeviceController().get_menu_items_by_category(**REQUEST_ARGS)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {"status": "error", "message": SERVER_ERROR}
        session.rollback.assert_called_once_with()
