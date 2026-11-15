from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    SERVER_ERROR,
)
from app.models.responses.menu_category_response import (
    MenuCategoryListResponse,
    MenuCategoryPaginationResponse,
    MenuCategoryResponse,
)


class TestGetMenuCategories:
    """StoreController のメニューカテゴリー取得処理を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_get_menu_categories(self, mock_service_class) -> None:
        """サービスのカテゴリー取得結果をそのまま返すことを確認する。"""
        mysql_session = Mock()
        expected = MenuCategoryListResponse(
            menu_categories=[
                MenuCategoryResponse(
                    menu_category_id=1,
                    name="ハンバーガー",
                    image_url="https://example.com/categories/101/1.png",
                    display_order=1,
                    is_active=True,
                )
            ],
            pagination=MenuCategoryPaginationResponse(
                page=1,
                page_size=20,
                total=1,
                total_pages=1,
            ),
        )
        mock_service_class.return_value.get_menu_categories.return_value = expected

        result = StoreController.get_menu_categories.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            is_active=True,
            page=1,
            page_size=20,
        )

        assert result == expected
        mock_service_class.return_value.get_menu_categories.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            is_active=True,
            page=1,
            page_size=20,
        )

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_get_menu_categories_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """カテゴリー取得時の想定外例外を500へ変換することを確認する。"""
        mock_service_class.return_value.get_menu_categories.side_effect = Exception(
            "unexpected error"
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_menu_categories.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
