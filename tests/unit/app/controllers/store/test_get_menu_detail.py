"""メニュー詳細取得Controllerのテスト。"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import MenuItemNotFoundException
from app.core.exceptions.message import MENU_ITEM_NOT_FOUND_ERROR, SERVER_ERROR
from app.models.responses.menu_detail_response import MenuDetailResponse


class TestGetMenuDetail:
    """StoreControllerのメニュー詳細取得を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_get_menu_detail(self, mock_service_class) -> None:
        """Serviceのメニュー詳細取得結果をそのまま返す。"""
        mysql_session = Mock()
        expected = MenuDetailResponse(
            menu_item_id=10,
            menu_category_id=None,
            menu_category_name=None,
            name="未分類商品",
            description=None,
            price="300.000000",
            token_symbol="JPYC",
            image_url="https://example.com/menus/101/10.png",
            is_available=True,
            display_order=1,
            option_groups=[],
        )
        mock_service_class.return_value.get_menu_detail.return_value = expected

        result = StoreController.get_menu_detail.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=10,
        )

        assert result == expected
        mock_service_class.return_value.get_menu_detail.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=10,
        )

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_get_menu_detail_returns_not_found(self, mock_service_class) -> None:
        """商品未存在例外を404のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.get_menu_detail.side_effect = (
            MenuItemNotFoundException()
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_menu_detail.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=999,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": MENU_ITEM_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_get_menu_detail_returns_server_error(self, mock_service_class) -> None:
        """予期しない例外を500のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.get_menu_detail.side_effect = Exception(
            "unexpected error"
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_menu_detail.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=10,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
