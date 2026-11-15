"""メニュー基本情報更新Controllerのテスト。"""

from decimal import Decimal
from unittest.mock import ANY, Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import (
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
    MenuItemNotFoundException,
)
from app.core.exceptions.message import (
    MENU_CATEGORY_NOT_FOUND_ERROR,
    MENU_IMAGE_INVALID_ERROR,
    MENU_ITEM_NOT_FOUND_ERROR,
    SERVER_ERROR,
)
from app.models.requests.menu_update_request import MenuUpdateRequest
from app.models.responses.menu_update_response import MenuUpdateResponse


def _build_request() -> MenuUpdateRequest:
    """Controllerテスト用の更新リクエストを生成する。

    Returns:
        テスト用メニュー基本情報更新リクエスト。
    """
    return MenuUpdateRequest(
        menu_category_id=12,
        name="更新商品",
        description="更新後の説明",
        price=Decimal("950.000000"),
        token_symbol="JPYC",
        is_available=False,
        display_order=3,
    )


class TestUpdateMenu:
    """StoreControllerのメニュー基本情報更新を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_update_menu(self, mock_service_class) -> None:
        """Serviceのメニュー更新結果をそのまま返す。"""
        request = _build_request()
        expected = MenuUpdateResponse(
            menu_item_id=21,
        )
        mock_service_class.return_value.update_menu.return_value = expected

        result = StoreController.update_menu.__wrapped__(
            StoreController(),
            mysql_session=Mock(),
            store_id=101,
            menu_item_id=21,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.update_menu.assert_called_once_with(
            mysql_session=ANY,
            store_id=101,
            menu_item_id=21,
            request=request,
        )

    @pytest.mark.parametrize(
        ("exception", "status_code", "message"),
        [
            (MenuItemNotFoundException(), 404, MENU_ITEM_NOT_FOUND_ERROR),
            (MenuCategoryNotFoundException(), 404, MENU_CATEGORY_NOT_FOUND_ERROR),
            (MenuImageInvalidException(), 422, MENU_IMAGE_INVALID_ERROR),
            (Exception(), 500, SERVER_ERROR),
        ],
    )
    @patch("app.controllers.store_controller.StoreMenuService")
    def test_maps_service_exception(
        self,
        mock_service_class,
        exception,
        status_code,
        message,
    ) -> None:
        """Service例外を対応するHTTPExceptionへ変換する。"""
        mock_service_class.return_value.update_menu.side_effect = exception

        with pytest.raises(HTTPException) as exc_info:
            StoreController.update_menu.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=21,
                request=_build_request(),
            )

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
