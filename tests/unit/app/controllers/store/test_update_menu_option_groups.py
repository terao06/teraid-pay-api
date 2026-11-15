"""メニューオプション構成更新Controllerのテスト。"""

from unittest.mock import ANY, Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import (
    MenuItemNotFoundException,
    MenuOptionConfigurationInvalidException,
)
from app.core.exceptions.message import (
    MENU_ITEM_NOT_FOUND_ERROR,
    MENU_OPTION_CONFIGURATION_INVALID_ERROR,
    SERVER_ERROR,
)
from app.models.requests.menu_option_groups_update_request import (
    MenuOptionGroupsUpdateRequest,
)
from app.models.responses.menu_option_groups_update_response import (
    MenuOptionGroupsUpdateResponse,
)


class TestUpdateMenuOptionGroups:
    """StoreControllerのオプション構成更新を検証する。"""

    @patch("app.controllers.store_controller.StoreMenuService")
    def test_returns_service_result(self, mock_service_class) -> None:
        """Serviceの更新結果をそのまま返す。"""
        request = MenuOptionGroupsUpdateRequest(option_groups=[])
        expected = MenuOptionGroupsUpdateResponse(
            menu_item_id=10,
            menu_option_groups=[],
        )
        mock_service_class.return_value.update_menu_option_groups.return_value = (
            expected
        )

        result = StoreController.update_menu_option_groups.__wrapped__(
            StoreController(),
            mysql_session=Mock(),
            store_id=101,
            menu_item_id=10,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.update_menu_option_groups.assert_called_once_with(
            mysql_session=ANY,
            store_id=101,
            menu_item_id=10,
            request=request,
        )

    @pytest.mark.parametrize(
        ("exception", "status_code", "message"),
        [
            (MenuItemNotFoundException(), 404, MENU_ITEM_NOT_FOUND_ERROR),
            (
                MenuOptionConfigurationInvalidException(),
                422,
                MENU_OPTION_CONFIGURATION_INVALID_ERROR,
            ),
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
        mock_service_class.return_value.update_menu_option_groups.side_effect = (
            exception
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.update_menu_option_groups.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=10,
                request=MenuOptionGroupsUpdateRequest(option_groups=[]),
            )

        assert exc_info.value.status_code == status_code
        assert exc_info.value.detail == {"status": "error", "message": message}
