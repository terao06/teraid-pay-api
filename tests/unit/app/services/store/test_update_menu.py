"""メニュー基本情報更新Serviceのテスト。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest

from app.core.exceptions.custom_exception import (
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
    MenuItemNotFoundException,
)
from app.models.requests.menu_update_request import MenuUpdateRequest
from app.models.responses.menu_update_response import MenuUpdateResponse
from app.services.store_menu_service import StoreMenuService

from ._helpers import build_menu_image


def _build_request(**overrides) -> MenuUpdateRequest:
    """テスト用のメニュー基本情報更新リクエストを生成する。

    Args:
        overrides: 既定値から差し替えるフィールド。

    Returns:
        テスト用メニュー基本情報更新リクエスト。
    """
    values = {
        "menu_category_id": 12,
        "name": "更新商品",
        "description": "更新後の説明",
        "price": Decimal("950.000000"),
        "token_symbol": "JPYC",
        "is_available": False,
        "display_order": 3,
    }
    values.update(overrides)
    return MenuUpdateRequest(**values)


class TestUpdateMenu:
    """StoreMenuServiceのメニュー基本情報更新を検証する。"""

    @patch("app.services.store_menu_service.S3Client")
    @patch("app.services.store_menu_service.SsmClient")
    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_updates_menu_without_replacing_image(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """画像を変更せず商品基本情報だけを更新する。"""
        mysql_session = Mock()
        item = SimpleNamespace(
            menu_item_id=21,
            menu_category_id=11,
            name="更新前",
            description=None,
            price=Decimal("800.000000"),
            token_symbol="JPYC",
            image_extension="jpeg",
            is_available=True,
            display_order=1,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_item_for_update.return_value = item
        repository.get_active_menu_category.return_value = SimpleNamespace(
            menu_category_id=12
        )
        repository.update_menu_item.side_effect = (
            lambda mysql_session, menu_item: menu_item
        )
        request = _build_request()

        result = StoreMenuService().update_menu(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=21,
            request=request,
        )

        assert result == MenuUpdateResponse(
            menu_item_id=21,
        )
        repository.get_menu_item_for_update.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=21,
        )
        repository.get_active_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=12,
        )
        repository.update_menu_item.assert_called_once_with(
            mysql_session=mysql_session,
            menu_item=item,
        )
        assert item.image_extension == "jpeg"
        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()

    @patch("app.services.store_menu_service.S3Client")
    @patch("app.services.store_menu_service.SsmClient")
    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_replaces_image_and_registers_rollback_compensation(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """拡張子変更時に新画像削除と旧画像復元を登録する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        item = SimpleNamespace(
            menu_item_id=21,
            menu_category_id=12,
            name="更新前",
            description=None,
            price=Decimal("800.000000"),
            token_symbol="JPYC",
            image_extension="png",
            is_available=True,
            display_order=1,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_item_for_update.return_value = item
        repository.get_active_menu_category.return_value = SimpleNamespace(
            menu_category_id=12
        )
        repository.update_menu_item.side_effect = (
            lambda mysql_session, menu_item: menu_item
        )
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
        )
        s3_client = mock_s3_client_class.return_value
        s3_client.get_object.return_value = b"old-image"
        request = _build_request(
            menu_image=build_menu_image(format="JPEG"),
            image_extension="jpg",
        )

        StoreMenuService().update_menu(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=21,
            request=request,
        )

        assert item.image_extension == "jpg"
        s3_client.get_object.assert_called_once_with(
            bucket_name="menus",
            key="101/21.png",
        )
        s3_client.delete_object.assert_called_once_with(
            bucket_name="menus",
            file_name="101/21.png",
        )
        callback = mysql_session.info["mysql_rollback_callbacks"][0]
        callback()
        assert s3_client.delete_object.call_args_list == [
            call(bucket_name="menus", file_name="101/21.png"),
            call(bucket_name="menus", file_name="101/21.jpg"),
        ]
        restored_upload = s3_client.upload_object.call_args
        assert restored_upload.kwargs["file_name"] == "101/21.png"
        assert restored_upload.kwargs["file"].read() == b"old-image"

    @pytest.mark.parametrize(
        ("item", "category", "expected_exception"),
        [
            (None, None, MenuItemNotFoundException),
            (
                SimpleNamespace(menu_item_id=21),
                None,
                MenuCategoryNotFoundException,
            ),
        ],
    )
    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_rejects_inaccessible_item_or_category(
        self,
        mock_repository_class,
        item,
        category,
        expected_exception,
    ) -> None:
        """商品またはカテゴリーを利用できない場合は専用例外を送出する。"""
        repository = mock_repository_class.return_value
        repository.get_menu_item_for_update.return_value = item
        repository.get_active_menu_category.return_value = category

        with pytest.raises(expected_exception):
            StoreMenuService().update_menu(
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=21,
                request=_build_request(),
            )

        repository.update_menu_item.assert_not_called()

    @patch("app.services.store_menu_service.S3Client")
    @patch("app.services.store_menu_service.SsmClient")
    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_rejects_invalid_menu_image(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """画像の実形式と拡張子が異なる場合は専用例外を送出する。"""
        repository = mock_repository_class.return_value
        repository.get_menu_item_for_update.return_value = SimpleNamespace(
            menu_item_id=21,
            image_extension="png",
        )
        repository.get_active_menu_category.return_value = SimpleNamespace(
            menu_category_id=12
        )

        with pytest.raises(MenuImageInvalidException):
            StoreMenuService().update_menu(
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=21,
                request=_build_request(
                    menu_image=build_menu_image(format="PNG"),
                    image_extension="jpg",
                ),
            )

        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
        repository.update_menu_item.assert_not_called()
