"""メニューカテゴリー更新Controllerのテスト。"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import (
    MenuCategoryImageInvalidException,
    MenuCategoryNotFoundException,
)
from app.core.exceptions.message import (
    MENU_CATEGORY_IMAGE_INVALID_ERROR,
    MENU_CATEGORY_NOT_FOUND_ERROR,
    SERVER_ERROR,
)
from app.models.requests.menu_category_update_request import (
    MenuCategoryUpdateRequest,
)
from app.models.responses.menu_category_response import MenuCategoryUpdateResponse


class TestUpdateMenuCategory:
    """StoreControllerのメニューカテゴリー更新を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_update_menu_category(self, mock_service_class) -> None:
        """サービスのカテゴリー更新結果をそのまま返す。"""
        mysql_session = Mock()
        request = MenuCategoryUpdateRequest(
            name="更新後",
            display_order=2,
            is_active=True,
        )
        expected = MenuCategoryUpdateResponse(
            menu_category_id=14,
        )
        mock_service_class.return_value.update_menu_category.return_value = expected

        result = StoreController.update_menu_category.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.update_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
            request=request,
        )

    @pytest.mark.parametrize(
        ("exception", "status_code", "message"),
        [
            (MenuCategoryNotFoundException(), 404, MENU_CATEGORY_NOT_FOUND_ERROR),
            (
                MenuCategoryImageInvalidException(),
                422,
                MENU_CATEGORY_IMAGE_INVALID_ERROR,
            ),
            (Exception(), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    def test_maps_service_exception(
        self,
        mock_service_class,
        exception,
        status_code,
        message,
    ) -> None:
        """サービス例外を対応するHTTPExceptionへ変換する。"""
        mock_service_class.return_value.update_menu_category.side_effect = exception

        with pytest.raises(HTTPException) as exc_info:
            StoreController.update_menu_category.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_category_id=14,
                request=MenuCategoryUpdateRequest(
                    name="更新後",
                    display_order=2,
                    is_active=True,
                ),
            )

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": message,
        }
