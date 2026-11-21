"""メニューカテゴリー画像の署名付きGET URLを生成する。"""

from functools import cached_property

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.models.mysql.menu_category import MenuCategory


class MenuCategoryImageHelper:
    """メニューカテゴリー画像の署名付きURL生成を共通化する。

    Args:
        なし。

    Returns:
        メニューカテゴリー画像のURLを生成するヘルパー。
    """

    def generate_presigned_get_url(
        self,
        store_id: int,
        category: MenuCategory,
    ) -> str:
        """店舗とカテゴリーに対応する画像の署名付きGET URLを生成する。

        Args:
            store_id: 対象カテゴリーの所属店舗ID。
            category: 画像のIDと拡張子を持つメニューカテゴリー。

        Returns:
            設定された有効期限で署名済みの画像URL。
        """
        client, params = self._client_and_params
        return client.generate_presigned_get_url(
            bucket_name=params.category_image_bucket,
            file_name=f"{store_id}/{category.menu_category_id}.{category.image_extension}",
            expires_in=params.menu_image_url_expires_in,
        )

    @cached_property
    def _client_and_params(self) -> tuple[S3Client, SsmClient]:
        """最初の署名時にAWSの設定とクライアントを用意し、同じHelper内で再利用する。"""
        params = SsmClient()
        return S3Client(s3_endpoint=params.s3_endpoint), params
