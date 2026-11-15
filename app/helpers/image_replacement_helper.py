"""S3画像の差し替えとトランザクション失敗時の復元処理を提供する。"""

from enum import Enum
from io import BytesIO

from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import InvalidImageError
from app.core.utils.image import ImageUtil
from app.middlewares.transaction import add_mysql_rollback_callback


class ImageBucketType(Enum):
    """画像差し替えで使用するS3バケットのSSM設定属性を表す。

    Args:
        なし。

    Returns:
        SsmClientからバケット名を取得するための属性名。
    """

    MENU = "menu_image_bucket"
    CATEGORY = "category_image_bucket"


class ImageReplacementHelper:
    """画像の検証、S3上の差し替え、ロールバック補償を共通化する。

    Args:
        なし。

    Returns:
        画像差し替えHelper。
    """

    def replace_image(
        self,
        mysql_session: Session,
        image_content: str,
        old_key: str,
        new_key: str,
        old_extension: str,
        new_extension: str,
        image_bucket_type: ImageBucketType,
    ) -> None:
        """S3画像を差し替え、DB失敗時に旧画像を復元する処理を登録する。

        Args:
            mysql_session: 補償処理を登録するSQLAlchemyセッション。
            image_content: Base64形式の新しい画像。
            old_key: 差し替え前画像のS3オブジェクトキー。
            new_key: 差し替え後画像のS3オブジェクトキー。
            old_extension: 差し替え前画像の拡張子。
            new_extension: 差し替え後画像の拡張子。
            image_bucket_type: 画像を保存するS3バケットの種別。

        Returns:
            なし。

        Raises:
            InvalidImageError: 新しい画像を読み込めない場合。
        """
        try:
            new_image_bytes = ImageUtil.decode_base64_image(
                content=image_content,
                image_extension=new_extension,
            )
        except ValueError as exc:
            raise InvalidImageError("画像を読み込めません。") from exc

        params = SsmClient()
        bucket_name = getattr(params, image_bucket_type.value)
        client = S3Client(s3_endpoint=params.s3_endpoint)
        old_image_bytes = client.get_object(
            bucket_name=bucket_name,
            key=old_key,
        )
        add_mysql_rollback_callback(
            mysql_session=mysql_session,
            callback=lambda: self._restore_image(
                client=client,
                bucket_name=bucket_name,
                old_key=old_key,
                old_image_bytes=old_image_bytes,
                old_extension=old_extension,
                new_key=new_key,
            ),
        )
        client.upload_object(
            bucket_name=bucket_name,
            file=BytesIO(new_image_bytes),
            file_name=new_key,
            content_type=ImageUtil.get_content_type(
                image_extension=new_extension,
            ),
        )
        if new_key != old_key:
            client.delete_object(
                bucket_name=bucket_name,
                file_name=old_key,
            )

    @staticmethod
    def _restore_image(
        client: S3Client,
        bucket_name: str,
        old_key: str,
        old_image_bytes: bytes,
        old_extension: str,
        new_key: str,
    ) -> None:
        """新画像を取り除き、差し替え前の画像をS3へ復元する。

        Args:
            client: S3操作に使用するクライアント。
            bucket_name: 画像を保存するバケット名。
            old_key: 復元する旧画像のS3オブジェクトキー。
            old_image_bytes: 差し替え前に退避した画像データ。
            old_extension: 旧画像の拡張子。
            new_key: 削除対象となる新画像のS3オブジェクトキー。

        Returns:
            なし。
        """
        try:
            if new_key != old_key:
                client.delete_object(
                    bucket_name=bucket_name,
                    file_name=new_key,
                )
        finally:
            client.upload_object(
                bucket_name=bucket_name,
                file=BytesIO(old_image_bytes),
                file_name=old_key,
                content_type=ImageUtil.get_content_type(
                    image_extension=old_extension,
                ),
            )
