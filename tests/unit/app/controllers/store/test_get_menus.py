from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    SERVER_ERROR,
)
from app.models.responses.menu_list_response import (
    MenuItemResponse,
    MenuListResponse,
)


class TestGetMenus:
    """StoreController のメニュー一覧取得処理を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_get_menus(self, mock_service_class) -> None:
        """サービスのメニュー取得結果をそのまま返すことを確認する。"""
        mysql_session = Mock()
        expected = MenuListResponse(
            menu_items=[
                MenuItemResponse(
                    menu_item_id=10,
                    menu_category_id=1,
                    menu_category_name="ハンバーガー",
                    name="チーズバーガー",
                    description="チェダーチーズ入り",
                    price="800.000000",
                    token_symbol="JPYC",
                    image_url="https://s3.example.com/menus/101/10.jpeg",
                    is_available=True,
                    display_order=1,
                )
            ]
        )
        mock_service_class.return_value.get_menus.return_value = expected

        result = StoreController.get_menus.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            menu_category_id=12,
            is_available=True,
            page=2,
            page_size=10,
        )

        assert result == expected
        mock_service_class.return_value.get_menus.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            menu_category_id=12,
            is_available=True,
            page=2,
            page_size=10,
        )

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_get_menus_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """メニュー取得時の想定外例外を500へ変換することを確認する。"""
        mock_service_class.return_value.get_menus.side_effect = Exception(
            "unexpected error"
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.get_menus.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
