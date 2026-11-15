from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import (
    MENU_CATEGORY_NOT_FOUND_ERROR,
    MENU_IMAGE_INVALID_ERROR,
    SERVER_ERROR,
)
from app.core.exceptions.custom_exception import (
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
)
from app.models.requests.menu_create_request import (
    MenuCreateRequest,
    MenuOptionCreateRequest,
    MenuOptionGroupCreateRequest,
)
from app.models.responses.menu_create_response import (
    MenuCreateResponse,
    MenuOptionGroupCreateResponse,
)


class TestCreateMenu:
    """StoreController のメニュー登録処理を検証する。"""

    @patch("app.controllers.store_controller.StoreService")
    def test_create_menu(self, mock_service_class) -> None:
        """リクエストと店舗IDをサービスへ渡して登録結果を返すことを確認する。"""
        mysql_session = Mock()
        request = MenuCreateRequest(
            menu_category_id=12,
            name="チーズバーガー",
            description="チェダーチーズ入り",
            price="800.000000",
            menu_image="base64-encoded-image",
            image_extension="jpeg",
            option_groups=[
                MenuOptionGroupCreateRequest(
                    name="サイズ",
                    min_selections=1,
                    max_selections=1,
                    options=[
                        MenuOptionCreateRequest(name="通常"),
                    ],
                )
            ],
        )
        expected = MenuCreateResponse(
            menu_item_id=10,
            menu_option_groups=[
                MenuOptionGroupCreateResponse(
                    menu_option_group_id=20,
                    menu_option_ids=[30],
                )
            ],
        )
        mock_service_class.return_value.create_menu.return_value = expected

        result = StoreController.create_menu.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.create_menu.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

    @patch("app.controllers.store_controller.StoreService")
    def test_create_menu_raise_not_found_when_category_not_found(
        self,
        mock_service_class,
    ) -> None:
        """カテゴリー未存在例外を404のHTTPExceptionへ変換することを確認する。"""
        request = MenuCreateRequest(
            menu_category_id=999,
            name="チーズバーガー",
            price="800.000000",
            menu_image="base64-encoded-image",
            image_extension="jpeg",
            option_groups=[],
        )
        mock_service_class.return_value.create_menu.side_effect = (
            MenuCategoryNotFoundException()
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_menu.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "status": "error",
            "message": MENU_CATEGORY_NOT_FOUND_ERROR,
        }

    @patch("app.controllers.store_controller.StoreService")
    def test_create_menu_raise_unprocessable_when_menu_image_invalid(
        self,
        mock_service_class,
    ) -> None:
        """画像不正例外を422のHTTPExceptionへ変換することを確認する。"""
        request = MenuCreateRequest(
            name="チーズバーガー",
            price="800.000000",
            menu_image="invalid-image",
            image_extension="jpeg",
            option_groups=[],
        )
        mock_service_class.return_value.create_menu.side_effect = (
            MenuImageInvalidException()
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_menu.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == {
            "status": "error",
            "message": MENU_IMAGE_INVALID_ERROR,
        }

    @patch("app.controllers.store_controller.StoreService")
    def test_create_menu_raise_http_exception_when_service_fails(
        self,
        mock_service_class,
    ) -> None:
        """メニュー登録時の想定外例外を500へ変換することを確認する。"""
        request = MenuCreateRequest(
            name="チーズバーガー",
            price="800.000000",
            menu_image="base64-encoded-image",
            image_extension="jpeg",
            option_groups=[],
        )
        mock_service_class.return_value.create_menu.side_effect = Exception(
            "unexpected error"
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_menu.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == {
            "status": "error",
            "message": SERVER_ERROR,
        }
