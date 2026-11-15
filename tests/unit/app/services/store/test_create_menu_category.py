"""メニューカテゴリー登録Serviceのテスト。"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import MenuCategoryImageInvalidException
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.responses.menu_category_response import MenuCategoryCreateResponse
from app.services.store_menu_category_service import StoreMenuCategoryService

from ._helpers import build_menu_image


class TestCreateMenuCategory:
    """StoreMenuCategoryServiceのカテゴリー登録処理を検証する。"""

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_create_menu_category(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """カテゴリーを登録し、登録IDだけを返すことを確認する。"""

        mysql_session = Mock()
        mysql_session.info = {}
        request = MenuCategoryCreateRequest(
            name="ハンバーガー",
            category_image=build_menu_image(),
            image_extension="png",
            display_order=1,
            is_active=True,
        )
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            category_image_bucket="categories",
        )

        def save_category(mysql_session, menu_category):
            """登録対象へ採番済みIDを設定して返す。"""

            menu_category.menu_category_id = 18
            return menu_category

        mock_repository = mock_repository_class.return_value
        mock_repository.create_menu_category.side_effect = save_category

        result = StoreMenuCategoryService().create_menu_category(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == MenuCategoryCreateResponse(
            menu_category_id=18,
        )
        saved_category = mock_repository.create_menu_category.call_args.kwargs[
            "menu_category"
        ]
        assert saved_category.store_id == 101
        assert saved_category.image_extension == "png"
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        upload_kwargs = mock_s3_client_class.return_value.upload_object.call_args.kwargs
        assert upload_kwargs["bucket_name"] == "categories"
        assert upload_kwargs["file_name"] == "101/18.png"
        assert upload_kwargs["content_type"] == "image/png"
        assert upload_kwargs["file"].read() != b""
        assert len(mysql_session.info["mysql_rollback_callbacks"]) == 1

    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_rejects_invalid_category_image(self, mock_repository_class) -> None:
        """画像形式と拡張子が一致しない場合は例外を送出する。"""

        request = MenuCategoryCreateRequest(
            name="ハンバーガー",
            category_image=build_menu_image(format="PNG"),
            image_extension="jpeg",
        )

        with pytest.raises(MenuCategoryImageInvalidException):
            StoreMenuCategoryService().create_menu_category(
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        mock_repository_class.assert_not_called()
