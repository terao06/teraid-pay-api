"""メニュー詳細取得Serviceのテスト。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import MenuItemNotFoundException
from app.models.responses.menu_detail_response import (
    MenuDetailResponse,
    MenuOptionGroupResponse,
    MenuOptionResponse,
)
from app.services.store_menu_service import StoreMenuService


class TestGetMenuDetail:
    """StoreMenuServiceのメニュー詳細取得処理を検証する。"""

    @patch("app.services.store_menu_service.S3Client")
    @patch("app.services.store_menu_service.SsmClient")
    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_get_menu_detail(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """JOIN結果をオプショングループ単位の階層へ集約する。"""
        mysql_session = Mock()
        item = SimpleNamespace(
            menu_item_id=10,
            menu_category_id=1,
            name="チーズバーガー",
            description="チェダーチーズ入り",
            price=Decimal("800.000000"),
            token_symbol="JPYC",
            image_extension="jpeg",
            is_available=False,
            display_order=1,
        )
        size_group = SimpleNamespace(
            menu_option_group_id=20,
            name="サイズ",
            min_selections=1,
            max_selections=1,
            display_order=1,
            is_active=False,
        )
        topping_group = SimpleNamespace(
            menu_option_group_id=21,
            name="トッピング",
            min_selections=0,
            max_selections=2,
            display_order=2,
            is_active=True,
        )
        regular_option = SimpleNamespace(
            menu_option_id=30,
            name="通常",
            additional_price=Decimal("0.000000"),
            display_order=1,
            is_available=True,
        )
        large_option = SimpleNamespace(
            menu_option_id=31,
            name="大盛り",
            additional_price=Decimal("100.000000"),
            display_order=2,
            is_available=False,
        )
        mock_repository_class.return_value.get_menu_detail.return_value = [
            (item, "ハンバーガー", size_group, regular_option),
            (item, "ハンバーガー", size_group, large_option),
            (item, "ハンバーガー", topping_group, None),
        ]
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
            menu_image_url_expires_in=3600,
        )
        mock_s3_client_class.return_value.generate_presigned_get_url.return_value = (
            "https://s3.example.com/menus/101/10.jpeg"
        )

        result = StoreMenuService().get_menu_detail(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=10,
        )

        assert result == MenuDetailResponse(
            menu_item_id=10,
            menu_category_id=1,
            menu_category_name="ハンバーガー",
            name="チーズバーガー",
            description="チェダーチーズ入り",
            price="800.000000",
            token_symbol="JPYC",
            image_url="https://s3.example.com/menus/101/10.jpeg",
            is_available=False,
            display_order=1,
            option_groups=[
                MenuOptionGroupResponse(
                    menu_option_group_id=20,
                    name="サイズ",
                    min_selections=1,
                    max_selections=1,
                    display_order=1,
                    is_active=False,
                    options=[
                        MenuOptionResponse(
                            menu_option_id=30,
                            name="通常",
                            additional_price="0.000000",
                            display_order=1,
                            is_available=True,
                        ),
                        MenuOptionResponse(
                            menu_option_id=31,
                            name="大盛り",
                            additional_price="100.000000",
                            display_order=2,
                            is_available=False,
                        ),
                    ],
                ),
                MenuOptionGroupResponse(
                    menu_option_group_id=21,
                    name="トッピング",
                    min_selections=0,
                    max_selections=2,
                    display_order=2,
                    is_active=True,
                    options=[],
                ),
            ],
        )
        mock_repository_class.return_value.get_menu_detail.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=10,
        )
        mock_s3_client_class.return_value.generate_presigned_get_url.assert_called_once_with(
            bucket_name="menus",
            file_name="101/10.jpeg",
            expires_in=3600,
        )

    @patch("app.services.store_menu_service.S3Client")
    @patch("app.services.store_menu_service.SsmClient")
    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_get_menu_detail_raises_when_not_found(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """商品が存在しない場合に専用例外を送出する。"""
        mock_repository_class.return_value.get_menu_detail.return_value = []

        with pytest.raises(MenuItemNotFoundException):
            StoreMenuService().get_menu_detail(
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=999,
            )

        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
