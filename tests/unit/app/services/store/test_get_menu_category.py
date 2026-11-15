"""メニューカテゴリー詳細取得Serviceのテスト。"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import MenuCategoryNotFoundException
from app.models.responses.menu_category_response import MenuCategoryResponse
from app.services.store_menu_category_service import StoreMenuCategoryService


class TestGetMenuCategory:
    """StoreMenuCategoryServiceのカテゴリー詳細取得を検証する。"""

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_get_menu_category(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """取得したカテゴリーを署名付き画像URLを含むレスポンスへ変換する。"""
        mysql_session = Mock()
        mock_repository_class.return_value.get_menu_category.return_value = (
            SimpleNamespace(
                menu_category_id=14,
                name="無効カテゴリー",
                image_extension="png",
                display_order=0,
                is_active=False,
            )
        )
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            category_image_bucket="categories",
            menu_image_url_expires_in=3600,
        )
        mock_s3_client_class.return_value.generate_presigned_get_url.return_value = (
            "https://example.com/categories/101/14.png"
        )

        result = StoreMenuCategoryService().get_menu_category(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
        )

        assert result == MenuCategoryResponse(
            menu_category_id=14,
            name="無効カテゴリー",
            image_url="https://example.com/categories/101/14.png",
            display_order=0,
            is_active=False,
        )
        mock_repository_class.return_value.get_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
        )
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        mock_s3_client_class.return_value.generate_presigned_get_url.assert_called_once_with(
            bucket_name="categories",
            file_name="101/14.png",
            expires_in=3600,
        )

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_get_menu_category_raises_when_not_found(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """カテゴリーが存在しない場合は専用例外を送出する。"""
        mock_repository_class.return_value.get_menu_category.return_value = None

        with pytest.raises(MenuCategoryNotFoundException):
            StoreMenuCategoryService().get_menu_category(
                mysql_session=Mock(),
                store_id=101,
                menu_category_id=999,
            )

        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
