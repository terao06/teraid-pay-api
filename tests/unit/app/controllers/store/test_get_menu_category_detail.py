"""メニューカテゴリー詳細取得Controllerのテスト。"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import MenuCategoryNotFoundException
from app.core.exceptions.message import MENU_CATEGORY_NOT_FOUND_ERROR, SERVER_ERROR
from app.models.responses.menu_category_response import MenuCategoryResponse


class TestGetMenuCategoryDetail:
    """StoreControllerのメニューカテゴリー詳細取得を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_get_menu_category_detail(self, mock_service_class) -> None:
        """サービスのカテゴリー詳細取得結果をそのまま返す。"""
        mysql_session = Mock()
        expected = MenuCategoryResponse(
            menu_category_id=14,
            name="無効カテゴリー",
            image_url="https://example.com/categories/101/14.png",
            display_order=0,
            is_active=False,
        )
        mock_service_class.return_value.get_menu_category_detail.return_value = expected

        result = StoreController.get_menu_category_detail.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
        )

        assert result == expected
        mock_service_class.return_value.get_menu_category_detail.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
        )

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_get_menu_category_detail_returns_not_found(self, mock_service_class) -> None:
        """カテゴリー未存在例外を404のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.get_menu_category_detail.side_effect = (
            MenuCategoryNotFoundException()
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_menu_category_detail.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_category_id=999,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": MENU_CATEGORY_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_get_menu_category_detail_returns_server_error(self, mock_service_class) -> None:
        """予期しない例外を500のHTTPExceptionへ変換する。"""
        mock_service_class.return_value.get_menu_category_detail.side_effect = Exception(
            "unexpected error"
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_menu_category_detail.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_category_id=14,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
