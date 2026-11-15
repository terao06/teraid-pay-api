from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.responses.menu_list_response import (
    MenuItemResponse,
    MenuListResponse,
)
from app.services.store_service import StoreService


class TestGetMenus:
    """StoreService のメニュー一覧取得処理を検証する。"""

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_get_menus(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """取得した商品とカテゴリー名を一覧レスポンスへ変換することを確認する。"""
        mysql_session = Mock()
        mock_repository_class.return_value.get_menu_items.return_value = [
            (
                SimpleNamespace(
                    menu_item_id=10,
                    menu_category_id=1,
                    name="チーズバーガー",
                    description="チェダーチーズ入り",
                    price=Decimal("800.000000"),
                    token_symbol="JPYC",
                    image_extension="jpeg",
                    is_available=True,
                    display_order=1,
                ),
                "ハンバーガー",
            )
        ]
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
            menu_image_url_expires_in=3600,
        )
        mock_s3_client_class.return_value.generate_presigned_get_url.return_value = (
            "https://s3.example.com/menus/101/10.jpeg"
        )

        result = StoreService().get_menus(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            menu_category_id=1,
            is_available=True,
        )

        assert result == MenuListResponse(
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
        mock_repository_class.return_value.get_menu_items.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            menu_category_id=1,
            is_available=True,
        )
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        mock_s3_client_class.return_value.generate_presigned_get_url.assert_called_once_with(
            bucket_name="menus",
            file_name="101/10.jpeg",
            expires_in=3600,
        )

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_get_menus_returns_empty_list(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """商品が存在しない場合に空の一覧を返すことを確認する。"""
        mock_repository_class.return_value.get_menu_items.return_value = []
        mysql_session = Mock()

        result = StoreService().get_menus(
            mysql_session=mysql_session,
            store_id=101,
        )

        assert result == MenuListResponse(menu_items=[])
        mock_repository_class.return_value.get_menu_items.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name=None,
            menu_category_id=None,
            is_available=None,
        )
        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
