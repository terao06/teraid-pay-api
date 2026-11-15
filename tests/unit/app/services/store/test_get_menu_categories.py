from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.responses.menu_category_response import (
    MenuCategoryListResponse,
    MenuCategoryPaginationResponse,
    MenuCategoryResponse,
)
from app.services.store_menu_category_service import StoreMenuCategoryService


class TestGetMenuCategories:
    """StoreMenuCategoryService のメニューカテゴリー取得処理を検証する。"""

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_get_menu_categories(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """取得したカテゴリーを一覧レスポンスへ変換することを確認する。"""
        mysql_session = Mock()
        mock_repository_class.return_value.count_menu_categories.return_value = 2
        mock_repository_class.return_value.get_menu_categories.return_value = [
            SimpleNamespace(
                menu_category_id=1,
                name="ハンバーガー",
                image_extension="png",
                display_order=1,
                is_active=True,
            ),
            SimpleNamespace(
                menu_category_id=2,
                name="ドリンク",
                image_extension="jpg",
                display_order=2,
                is_active=True,
            ),
        ]
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            category_image_bucket="categories",
            menu_image_url_expires_in=3600,
        )
        mock_s3_client_class.return_value.generate_presigned_get_url.side_effect = [
            "https://example.com/categories/101/1.png",
            "https://example.com/categories/101/2.jpg",
        ]

        result = StoreMenuCategoryService().get_menu_categories(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            is_active=True,
            page=1,
            page_size=20,
        )

        assert result == MenuCategoryListResponse(
            menu_categories=[
                MenuCategoryResponse(
                    menu_category_id=1,
                    name="ハンバーガー",
                    image_url="https://example.com/categories/101/1.png",
                    display_order=1,
                    is_active=True,
                ),
                MenuCategoryResponse(
                    menu_category_id=2,
                    name="ドリンク",
                    image_url="https://example.com/categories/101/2.jpg",
                    display_order=2,
                    is_active=True,
                ),
            ],
            pagination=MenuCategoryPaginationResponse(
                page=1,
                page_size=20,
                total=2,
                total_pages=1,
            ),
        )
        mock_repository_class.return_value.count_menu_categories.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            is_active=True,
        )
        mock_repository_class.return_value.get_menu_categories.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            is_active=True,
            offset=0,
            limit=20,
        )
        assert (
            mock_s3_client_class.return_value.generate_presigned_get_url.call_count
            == 2
        )
        first_call = (
            mock_s3_client_class.return_value.generate_presigned_get_url.call_args_list[0]
        )
        assert first_call.kwargs == {
            "bucket_name": "categories",
            "file_name": "101/1.png",
            "expires_in": 3600,
        }

    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_get_menu_categories_returns_empty_list(
        self,
        mock_repository_class,
    ) -> None:
        """カテゴリーが存在しない場合に空の一覧を返すことを確認する。"""
        mock_repository_class.return_value.count_menu_categories.return_value = 0

        result = StoreMenuCategoryService().get_menu_categories(
            mysql_session=Mock(),
            store_id=101,
        )

        assert result == MenuCategoryListResponse(
            menu_categories=[],
            pagination=MenuCategoryPaginationResponse(
                page=1,
                page_size=None,
                total=0,
                total_pages=0,
            ),
        )
        mock_repository_class.return_value.get_menu_categories.assert_not_called()
