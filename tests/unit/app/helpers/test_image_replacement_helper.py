"""画像差し替えHelperの単体テスト。"""

import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest
from PIL import Image

from app.core.exceptions.custom_exception import InvalidImageError
from app.helpers.image_replacement_helper import (
    ImageBucketType,
    ImageReplacementHelper,
)
from app.middlewares.transaction import MYSQL_ROLLBACK_CALLBACKS_KEY


def _build_image(image_format: str = "PNG") -> str:
    """テスト用画像をBase64文字列として生成する。

    Args:
        image_format: 生成する画像の形式。

    Returns:
        Base64エンコード済みの画像文字列。
    """
    image = Image.new("RGB", (16, 16), color=(255, 0, 0))
    with BytesIO() as buffer:
        image.save(buffer, format=image_format)
        return base64.b64encode(buffer.getvalue()).decode("ascii")


class TestImageReplacementHelper:
    """ImageReplacementHelperの画像差し替えと補償処理を検証する。"""

    @patch("app.helpers.image_replacement_helper.S3Client")
    @patch("app.helpers.image_replacement_helper.SsmClient")
    def test_rejects_invalid_image_before_creating_s3_client(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """不正画像の場合はAWS関連Factoryを呼び出さず共通例外を送出する。"""
        mysql_session = Mock()
        mysql_session.info = {}

        with pytest.raises(InvalidImageError, match="画像を読み込めません"):
            ImageReplacementHelper().replace_image(
                mysql_session=mysql_session,
                image_content="invalid-image",
                old_key="101/21.png",
                new_key="101/21.png",
                old_extension="png",
                new_extension="png",
                image_bucket_type=ImageBucketType.MENU,
            )

        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
        assert mysql_session.info == {}

    @patch("app.helpers.image_replacement_helper.S3Client")
    @patch("app.helpers.image_replacement_helper.SsmClient")
    def test_replaces_same_key_and_restores_old_image_on_rollback(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """同一キーの差し替えでは削除せず、ロールバック時に旧画像を復元する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
            category_image_bucket="categories",
        )
        client = mock_s3_client_class.return_value
        client.get_object.return_value = b"old-image"

        ImageReplacementHelper().replace_image(
            mysql_session=mysql_session,
            image_content=_build_image(),
            old_key="101/21.png",
            new_key="101/21.png",
            old_extension="png",
            new_extension="png",
            image_bucket_type=ImageBucketType.MENU,
        )

        mock_ssm_client_class.assert_called_once_with()
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        client.get_object.assert_called_once_with(
            bucket_name="menus",
            key="101/21.png",
        )
        first_upload = client.upload_object.call_args
        assert first_upload.kwargs["file_name"] == "101/21.png"
        assert first_upload.kwargs["content_type"] == "image/png"
        client.delete_object.assert_not_called()

        callback = mysql_session.info[MYSQL_ROLLBACK_CALLBACKS_KEY][0]
        callback()

        restored_upload = client.upload_object.call_args
        assert restored_upload.kwargs["file_name"] == "101/21.png"
        assert restored_upload.kwargs["content_type"] == "image/png"
        assert restored_upload.kwargs["file"].read() == b"old-image"
        client.delete_object.assert_not_called()

    @patch("app.helpers.image_replacement_helper.S3Client")
    @patch("app.helpers.image_replacement_helper.SsmClient")
    def test_replaces_new_key_and_restores_old_key_on_rollback(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """拡張子変更時は旧キーを削除し、ロールバック時に新キーを除去する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
            category_image_bucket="categories",
        )
        client = mock_s3_client_class.return_value
        client.get_object.return_value = b"old-image"

        ImageReplacementHelper().replace_image(
            mysql_session=mysql_session,
            image_content=_build_image(image_format="JPEG"),
            old_key="101/21.png",
            new_key="101/21.jpg",
            old_extension="png",
            new_extension="jpg",
            image_bucket_type=ImageBucketType.MENU,
        )

        client.delete_object.assert_called_once_with(
            bucket_name="menus",
            file_name="101/21.png",
        )
        callback = mysql_session.info[MYSQL_ROLLBACK_CALLBACKS_KEY][0]
        callback()

        assert client.delete_object.call_args_list == [
            call(bucket_name="menus", file_name="101/21.png"),
            call(bucket_name="menus", file_name="101/21.jpg"),
        ]
        restored_upload = client.upload_object.call_args
        assert restored_upload.kwargs["file_name"] == "101/21.png"
        assert restored_upload.kwargs["content_type"] == "image/png"
        assert restored_upload.kwargs["file"].read() == b"old-image"

    @patch("app.helpers.image_replacement_helper.S3Client")
    @patch("app.helpers.image_replacement_helper.SsmClient")
    def test_propagates_s3_error_without_converting_it(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """S3操作エラーは画像不正例外へ変換せず、そのまま上位へ送出する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
            category_image_bucket="categories",
        )
        client = mock_s3_client_class.return_value
        client.get_object.side_effect = RuntimeError("S3 get failed")

        with pytest.raises(RuntimeError, match="S3 get failed"):
            ImageReplacementHelper().replace_image(
                mysql_session=mysql_session,
                image_content=_build_image(),
                old_key="101/21.png",
                new_key="101/21.png",
                old_extension="png",
                new_extension="png",
                image_bucket_type=ImageBucketType.MENU,
            )

        client.upload_object.assert_not_called()
        assert mysql_session.info == {}
