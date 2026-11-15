"""メニューカテゴリー更新Serviceのテスト。"""

from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest

from app.core.exceptions.custom_exception import (
    MenuCategoryImageInvalidException,
    MenuCategoryNotFoundException,
)
from app.models.requests.menu_category_update_request import (
    MenuCategoryUpdateRequest,
)
from app.models.responses.menu_category_response import MenuCategoryUpdateResponse
from app.services.store_menu_category_service import StoreMenuCategoryService

from ._helpers import build_menu_image


class TestUpdateMenuCategory:
    """StoreMenuCategoryServiceのカテゴリー更新を検証する。"""

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_updates_category_without_replacing_image(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """画像指定がない場合はカテゴリー情報だけを更新する。"""
        mysql_session = Mock()
        category = SimpleNamespace(
            menu_category_id=14,
            name="更新前",
            image_extension="png",
            display_order=0,
            is_active=False,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_category.return_value = category
        repository.update_menu_category.side_effect = (
            lambda mysql_session, menu_category: menu_category
        )
        request = MenuCategoryUpdateRequest(
            name="更新後",
            display_order=2,
            is_active=True,
        )

        result = StoreMenuCategoryService().update_menu_category(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=14,
            request=request,
        )

        assert result == MenuCategoryUpdateResponse(
            menu_category_id=14,
            name="更新後",
            display_order=2,
            is_active=True,
        )
        repository.update_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            menu_category=category,
        )
        assert category.image_extension == "png"
        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_replaces_image_and_restores_same_key_on_rollback(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """同じ拡張子の画像差し替え時に旧画像を復元できるよう登録する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        category = SimpleNamespace(
            menu_category_id=12,
            name="更新前",
            image_extension="png",
            display_order=1,
            is_active=True,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_category.return_value = category
        repository.update_menu_category.side_effect = (
            lambda mysql_session, menu_category: menu_category
        )
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            category_image_bucket="categories",
        )
        s3_client = mock_s3_client_class.return_value
        s3_client.get_object.return_value = b"old-image"
        request = MenuCategoryUpdateRequest(
            name="更新後",
            category_image=build_menu_image(format="PNG"),
            image_extension="png",
            display_order=2,
            is_active=True,
        )

        StoreMenuCategoryService().update_menu_category(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=12,
            request=request,
        )

        s3_client.get_object.assert_called_once_with(
            bucket_name="categories",
            key="101/12.png",
        )
        new_upload = s3_client.upload_object.call_args
        assert new_upload.kwargs["file_name"] == "101/12.png"
        assert new_upload.kwargs["content_type"] == "image/png"
        assert new_upload.kwargs["file"].read() != b"old-image"
        s3_client.delete_object.assert_not_called()

        callback = mysql_session.info["mysql_rollback_callbacks"][0]
        callback()

        restored_upload = s3_client.upload_object.call_args
        assert restored_upload.kwargs["file_name"] == "101/12.png"
        assert restored_upload.kwargs["file"].read() == b"old-image"
        s3_client.delete_object.assert_not_called()

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_replaces_image_with_new_key_and_restores_old_key_on_rollback(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """拡張子変更時に新画像削除と旧画像復元の補償処理を登録する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        category = SimpleNamespace(
            menu_category_id=12,
            name="更新前",
            image_extension="png",
            display_order=1,
            is_active=True,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_category.return_value = category
        repository.update_menu_category.side_effect = (
            lambda mysql_session, menu_category: menu_category
        )
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            category_image_bucket="categories",
        )
        s3_client = mock_s3_client_class.return_value
        s3_client.get_object.return_value = b"old-image"
        request = MenuCategoryUpdateRequest(
            name="更新後",
            category_image=build_menu_image(format="JPEG"),
            image_extension="jpg",
            display_order=2,
            is_active=True,
        )

        StoreMenuCategoryService().update_menu_category(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=12,
            request=request,
        )

        assert category.image_extension == "jpg"
        s3_client.delete_object.assert_called_once_with(
            bucket_name="categories",
            file_name="101/12.png",
        )
        callback = mysql_session.info["mysql_rollback_callbacks"][0]
        callback()

        assert s3_client.delete_object.call_args_list == [
            call(bucket_name="categories", file_name="101/12.png"),
            call(bucket_name="categories", file_name="101/12.jpg"),
        ]
        restored_upload = s3_client.upload_object.call_args
        assert restored_upload.kwargs["file_name"] == "101/12.png"
        assert restored_upload.kwargs["content_type"] == "image/png"
        assert restored_upload.kwargs["file"].read() == b"old-image"

    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_raises_when_category_is_not_found(
        self,
        mock_repository_class,
    ) -> None:
        """対象カテゴリーが存在しない場合は専用例外を送出する。"""
        mock_repository_class.return_value.get_menu_category.return_value = None

        with pytest.raises(MenuCategoryNotFoundException):
            StoreMenuCategoryService().update_menu_category(
                mysql_session=Mock(),
                store_id=101,
                menu_category_id=999,
                request=MenuCategoryUpdateRequest(
                    name="更新後",
                    display_order=1,
                    is_active=True,
                ),
            )

        mock_repository_class.return_value.update_menu_category.assert_not_called()

    @patch("app.services.store_menu_category_service.S3Client")
    @patch("app.services.store_menu_category_service.SsmClient")
    @patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
    def test_rejects_invalid_category_image(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """画像の実形式と拡張子が一致しない場合は専用例外を送出する。"""
        mock_repository_class.return_value.get_menu_category.return_value = (
            SimpleNamespace(
                menu_category_id=12,
                name="更新前",
                image_extension="png",
                display_order=1,
                is_active=True,
            )
        )
        request = MenuCategoryUpdateRequest(
            name="更新後",
            category_image=build_menu_image(format="PNG"),
            image_extension="jpg",
            display_order=2,
            is_active=True,
        )

        with pytest.raises(MenuCategoryImageInvalidException):
            StoreMenuCategoryService().update_menu_category(
                mysql_session=Mock(),
                store_id=101,
                menu_category_id=12,
                request=request,
            )

        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
        mock_repository_class.return_value.update_menu_category.assert_not_called()
