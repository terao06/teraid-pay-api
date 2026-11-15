from unittest.mock import Mock, patch

from fastapi import HTTPException
import pytest

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import MenuCategoryImageInvalidException
from app.core.exceptions.message import MENU_CATEGORY_IMAGE_INVALID_ERROR, SERVER_ERROR
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.responses.menu_category_response import MenuCategoryCreateResponse


class TestCreateMenuCategory:
    @patch("app.controllers.store_controller.StoreService")
    def test_create_menu_category(self, mock_service_class) -> None:
        mysql_session = Mock()
        request = MenuCategoryCreateRequest(
            name="ハンバーガー",
            category_image="base64-encoded-image",
            image_extension="png",
            display_order=1,
        )
        expected = MenuCategoryCreateResponse(
            menu_category_id=18,
            name="ハンバーガー",
            display_order=1,
            is_active=True,
        )
        mock_service_class.return_value.create_menu_category.return_value = expected

        result = StoreController.create_menu_category.__wrapped__(
            StoreController(),
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == expected
        mock_service_class.return_value.create_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

    @patch("app.controllers.store_controller.StoreService")
    def test_maps_invalid_image_to_422(self, mock_service_class) -> None:
        request = MenuCategoryCreateRequest(
            name="ハンバーガー",
            category_image="invalid",
            image_extension="png",
        )
        mock_service_class.return_value.create_menu_category.side_effect = (
            MenuCategoryImageInvalidException()
        )

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_menu_category.__wrapped__(
                StoreController(),
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == {
            "status": "error",
            "message": MENU_CATEGORY_IMAGE_INVALID_ERROR,
        }

    @patch("app.controllers.store_controller.StoreService")
    def test_maps_unexpected_error_to_500(self, mock_service_class) -> None:
        request = MenuCategoryCreateRequest(
            name="ハンバーガー",
            category_image="image",
            image_extension="png",
        )
        mock_service_class.return_value.create_menu_category.side_effect = Exception()

        with pytest.raises(HTTPException) as exc_info:
            StoreController.create_menu_category.__wrapped__(
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
