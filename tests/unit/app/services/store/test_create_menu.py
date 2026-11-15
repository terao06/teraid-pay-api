from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

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
from app.services.store_service import StoreService


from ._helpers import build_menu_image


class TestCreateMenu:
    """StoreService のメニュー登録処理を検証する。"""

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_create_menu(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """商品、オプショングループ、オプションを順番に登録することを確認する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        request = MenuCreateRequest(
            menu_category_id=12,
            name="チーズバーガー",
            description="チェダーチーズ入り",
            price="800.000000",
            token_symbol="JPYC",
            menu_image=build_menu_image(),
            image_extension="png",
            is_available=True,
            display_order=1,
            option_groups=[
                MenuOptionGroupCreateRequest(
                    name="サイズ",
                    min_selections=1,
                    max_selections=1,
                    display_order=1,
                    is_active=True,
                    options=[
                        MenuOptionCreateRequest(
                            name="通常",
                            additional_price="0.000000",
                            display_order=1,
                            is_available=True,
                        ),
                        MenuOptionCreateRequest(
                            name="大盛り",
                            additional_price="100.000000",
                            display_order=2,
                            is_available=True,
                        ),
                    ],
                )
            ],
        )
        mock_repository = mock_repository_class.return_value
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
        )
        mock_s3_client = mock_s3_client_class.return_value
        call_order = []
        mock_repository.get_active_menu_category.return_value = SimpleNamespace(
            menu_category_id=12
        )

        def save_menu_item(mysql_session, menu_item):
            call_order.append("menu_item")
            menu_item.menu_item_id = 10
            return menu_item

        def save_menu_option_group(mysql_session, menu_option_group):
            call_order.append("menu_option_group")
            menu_option_group.menu_option_group_id = 20
            return menu_option_group

        menu_option_ids = iter([30, 31])

        def save_menu_option(mysql_session, menu_option):
            call_order.append("menu_option")
            menu_option.menu_option_id = next(menu_option_ids)
            return menu_option

        mock_repository.create_menu_item.side_effect = save_menu_item
        mock_repository.create_menu_option_group.side_effect = (
            save_menu_option_group
        )
        mock_repository.create_menu_option.side_effect = save_menu_option
        mock_s3_client.upload_object.side_effect = (
            lambda **kwargs: call_order.append("s3_upload")
        )

        result = StoreService().create_menu(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == MenuCreateResponse(
            menu_item_id=10,
            menu_option_groups=[
                MenuOptionGroupCreateResponse(
                    menu_option_group_id=20,
                    menu_option_ids=[30, 31],
                )
            ],
        )
        mock_repository.get_active_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=12,
        )
        saved_menu_item = mock_repository.create_menu_item.call_args.kwargs[
            "menu_item"
        ]
        assert saved_menu_item.store_id == 101
        assert saved_menu_item.menu_category_id == 12
        assert saved_menu_item.name == "チーズバーガー"
        assert saved_menu_item.price == Decimal("800.000000")
        assert saved_menu_item.image_extension == "png"
        assert mock_repository.create_menu_option_group.call_count == 1
        assert mock_repository.create_menu_option.call_count == 2
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        mock_s3_client.upload_object.assert_called_once()
        upload_kwargs = mock_s3_client.upload_object.call_args.kwargs
        assert upload_kwargs["bucket_name"] == "menus"
        assert upload_kwargs["file_name"] == "101/10.png"
        assert upload_kwargs["content_type"] == "image/png"
        assert upload_kwargs["file"].read() != b""
        assert len(mysql_session.info["mysql_rollback_callbacks"]) == 1
        assert call_order == [
            "menu_item",
            "menu_option_group",
            "menu_option",
            "menu_option",
            "s3_upload",
        ]

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_create_menu_without_category(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """カテゴリー未指定の場合にカテゴリー検索を行わず登録することを確認する。"""
        request = MenuCreateRequest(
            name="カテゴリーなし商品",
            price="500.000000",
            menu_image=build_menu_image(format="JPEG"),
            image_extension="jpeg",
            option_groups=[],
        )
        mock_repository = mock_repository_class.return_value
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
        )
        mysql_session = Mock()
        mysql_session.info = {}

        def save_menu_item(mysql_session, menu_item):
            menu_item.menu_item_id = 11
            return menu_item

        mock_repository.create_menu_item.side_effect = save_menu_item

        result = StoreService().create_menu(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == MenuCreateResponse(
            menu_item_id=11,
            menu_option_groups=[],
        )
        mock_repository.get_active_menu_category.assert_not_called()
        mock_repository.create_menu_option_group.assert_not_called()
        mock_repository.create_menu_option.assert_not_called()
        mock_s3_client_class.return_value.upload_object.assert_called_once()

    @patch("app.services.store_service.StoreRepository")
    def test_create_menu_raise_when_category_not_found(
        self,
        mock_repository_class,
    ) -> None:
        """有効なカテゴリーが存在しない場合に登録処理を行わないことを確認する。"""
        request = MenuCreateRequest(
            menu_category_id=999,
            name="チーズバーガー",
            price="800.000000",
            menu_image=build_menu_image(),
            image_extension="png",
            option_groups=[],
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_active_menu_category.return_value = None

        with pytest.raises(MenuCategoryNotFoundException):
            StoreService().create_menu(
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        mock_repository.create_menu_item.assert_not_called()
        mock_repository.create_menu_option_group.assert_not_called()
        mock_repository.create_menu_option.assert_not_called()

    @patch("app.services.store_service.StoreRepository")
    def test_create_menu_raise_when_menu_image_invalid(
        self,
        mock_repository_class,
    ) -> None:
        """Base64画像と拡張子が一致しない場合にDB登録を行わないことを確認する。"""
        request = MenuCreateRequest(
            name="画像不正商品",
            price="800.000000",
            menu_image=build_menu_image(format="PNG"),
            image_extension="jpeg",
            option_groups=[],
        )

        with pytest.raises(MenuImageInvalidException):
            StoreService().create_menu(
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        mock_repository_class.assert_not_called()
