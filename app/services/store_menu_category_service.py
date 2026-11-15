"""店舗メニューカテゴリーのユースケースを提供するService。"""

from io import BytesIO
from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import (
    MenuCategoryImageInvalidException,
    MenuCategoryNotFoundException,
)
from app.core.utils.image import ImageUtil
from app.middlewares.transaction import add_mysql_rollback_callback
from app.models.mysql.menu_category import MenuCategory
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.requests.menu_category_update_request import MenuCategoryUpdateRequest
from app.models.responses.menu_category_response import (
    MenuCategoryCreateResponse, MenuCategoryListResponse,
    MenuCategoryPaginationResponse, MenuCategoryResponse,
    MenuCategoryUpdateResponse,
)
from app.repositories.mysql.store_menu_category_repository import StoreMenuCategoryRepository


class StoreMenuCategoryService:
    """カテゴリーの検索、登録、画像保存を調整する。"""

    def get_menu_categories(self, mysql_session: Session, store_id: int, name: str | None = None,
                            is_active: bool = True, page: int = 1,
                            page_size: int | None = None) -> MenuCategoryListResponse:
        """店舗のメニューカテゴリーを検索して画像URL付きで返す。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: カテゴリー名の部分一致条件。
            is_active: 有効状態の完全一致条件。
            page: 取得するページ番号。
            page_size: 1ページの件数。Noneの場合は全件取得する。

        Returns:
            カテゴリー一覧とページネーション情報。
        """
        repository = StoreMenuCategoryRepository()
        total = repository.count_menu_categories(
            mysql_session=mysql_session, store_id=store_id, name=name, is_active=is_active)
        response_page = page if page_size is not None else 1
        total_pages = ((total + page_size - 1) // page_size if page_size is not None
                       else (1 if total > 0 else 0))
        pagination = MenuCategoryPaginationResponse(
            page=response_page, page_size=page_size, total=total, total_pages=total_pages)
        if total == 0:
            return MenuCategoryListResponse(menu_categories=[], pagination=pagination)
        categories = repository.get_menu_categories(
            mysql_session=mysql_session, store_id=store_id, name=name, is_active=is_active,
            offset=(page - 1) * page_size if page_size is not None else 0, limit=page_size)
        if not categories:
            return MenuCategoryListResponse(menu_categories=[], pagination=pagination)
        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        responses = []
        for category in categories:
            key = f"{store_id}/{category.menu_category_id}.{category.image_extension}"
            responses.append(MenuCategoryResponse(
                menu_category_id=category.menu_category_id, name=category.name,
                image_url=client.generate_presigned_get_url(
                    bucket_name=params.category_image_bucket, file_name=key,
                    expires_in=params.menu_image_url_expires_in),
                display_order=category.display_order, is_active=category.is_active))
        return MenuCategoryListResponse(menu_categories=responses, pagination=pagination)

    def get_menu_category_detail(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
    ) -> MenuCategoryResponse:
        """店舗に属するメニューカテゴリー詳細を画像URL付きで取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 取得対象の店舗ID。
            menu_category_id: 取得対象のメニューカテゴリーID。

        Returns:
            画像の署名付きURLを含むメニューカテゴリー詳細。

        Raises:
            MenuCategoryNotFoundException: 対象カテゴリーが存在しない場合。
        """
        category = StoreMenuCategoryRepository().get_menu_category_detail(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
        )
        if category is None:
            raise MenuCategoryNotFoundException(
                "メニューカテゴリーが存在しません。"
            )

        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        key = f"{store_id}/{category.menu_category_id}.{category.image_extension}"
        return MenuCategoryResponse(
            menu_category_id=category.menu_category_id,
            name=category.name,
            image_url=client.generate_presigned_get_url(
                bucket_name=params.category_image_bucket,
                file_name=key,
                expires_in=params.menu_image_url_expires_in,
            ),
            display_order=category.display_order,
            is_active=category.is_active,
        )

    def update_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
        request: MenuCategoryUpdateRequest,
    ) -> MenuCategoryUpdateResponse:
        """店舗に属するメニューカテゴリーと任意の画像を更新する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 更新対象の店舗ID。
            menu_category_id: 更新対象のメニューカテゴリーID。
            request: カテゴリー名、任意の画像、表示順、有効状態を含む更新情報。

        Returns:
            更新済みのメニューカテゴリー情報。

        Raises:
            MenuCategoryNotFoundException: 対象カテゴリーが存在しない場合。
            MenuCategoryImageInvalidException: 更新画像を読み込めない場合。
        """
        repository = StoreMenuCategoryRepository()
        category = repository.get_menu_category_detail(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
        )
        if category is None:
            raise MenuCategoryNotFoundException(
                "メニューカテゴリーが存在しません。"
            )

        if request.category_image is not None and request.image_extension is not None:
            self._replace_category_image(
                mysql_session=mysql_session,
                store_id=store_id,
                category=category,
                category_image=request.category_image,
                image_extension=request.image_extension.value,
            )
            category.image_extension = request.image_extension.value

        category.name = request.name
        category.display_order = request.display_order
        category.is_active = request.is_active
        updated_category = repository.update_menu_category(
            mysql_session=mysql_session,
            menu_category=category,
        )
        return MenuCategoryUpdateResponse(
            menu_category_id=updated_category.menu_category_id,
            name=updated_category.name,
            display_order=updated_category.display_order,
            is_active=updated_category.is_active,
        )

    def _replace_category_image(
        self,
        mysql_session: Session,
        store_id: int,
        category: MenuCategory,
        category_image: str,
        image_extension: str,
    ) -> None:
        """カテゴリー画像を差し替え、DBロールバック時の復元処理を登録する。

        Args:
            mysql_session: 補償処理を紐づけるSQLAlchemyのセッション。
            store_id: 更新対象の店舗ID。
            category: 更新対象のメニューカテゴリー。
            category_image: Base64形式の新しいカテゴリー画像。
            image_extension: 新しいカテゴリー画像の拡張子。

        Returns:
            なし。

        Raises:
            MenuCategoryImageInvalidException: 更新画像を読み込めない場合。
        """
        try:
            new_image_bytes = ImageUtil.decode_base64_image(
                content=category_image,
                image_extension=image_extension,
            )
        except ValueError as exc:
            raise MenuCategoryImageInvalidException(
                "カテゴリー画像を読み込めません。"
            ) from exc

        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        old_extension = category.image_extension
        old_key = f"{store_id}/{category.menu_category_id}.{old_extension}"
        new_key = f"{store_id}/{category.menu_category_id}.{image_extension}"
        old_image_bytes = client.get_object(
            bucket_name=params.category_image_bucket,
            key=old_key,
        )
        add_mysql_rollback_callback(
            mysql_session=mysql_session,
            callback=lambda: self._restore_category_image(
                client=client,
                bucket_name=params.category_image_bucket,
                old_key=old_key,
                old_image_bytes=old_image_bytes,
                old_extension=old_extension,
                new_key=new_key,
            ),
        )
        client.upload_object(
            bucket_name=params.category_image_bucket,
            file=BytesIO(new_image_bytes),
            file_name=new_key,
            content_type=ImageUtil.get_content_type(
                image_extension=image_extension,
            ),
        )
        if new_key != old_key:
            client.delete_object(
                bucket_name=params.category_image_bucket,
                file_name=old_key,
            )

    @staticmethod
    def _restore_category_image(
        client: S3Client,
        bucket_name: str,
        old_key: str,
        old_image_bytes: bytes,
        old_extension: str,
        new_key: str,
    ) -> None:
        """新画像を除去し、メモリに保持した旧画像をS3へ復元する。

        Args:
            client: S3操作に使用するクライアント。
            bucket_name: カテゴリー画像を保存するバケット名。
            old_key: 復元する旧画像のオブジェクトキー。
            old_image_bytes: メモリに保持した旧画像データ。
            old_extension: 旧画像の拡張子。
            new_key: 削除対象となる新画像のオブジェクトキー。

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

    def create_menu_category(self, mysql_session: Session, store_id: int,
                             request: MenuCategoryCreateRequest) -> MenuCategoryCreateResponse:
        """メニューカテゴリーとカテゴリー画像を登録する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 登録先店舗ID。
            request: カテゴリー名、画像、表示順、有効状態を含む登録リクエスト。

        Returns:
            登録されたカテゴリー情報。

        Raises:
            MenuCategoryImageInvalidException: Base64画像をデコードできない場合。
        """
        try:
            image_bytes = ImageUtil.decode_base64_image(
                content=request.category_image, image_extension=request.image_extension.value)
        except ValueError as exc:
            raise MenuCategoryImageInvalidException("カテゴリー画像を読み込めません。") from exc
        category = StoreMenuCategoryRepository().create_menu_category(
            mysql_session=mysql_session, menu_category=MenuCategory(store_id=store_id, name=request.name,
                                        image_extension=request.image_extension.value,
                                        display_order=request.display_order, is_active=request.is_active))
        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        key = f"{store_id}/{category.menu_category_id}.{request.image_extension.value}"
        client.upload_object(bucket_name=params.category_image_bucket, file=BytesIO(image_bytes),
                             file_name=key, content_type=ImageUtil.get_content_type(
                                 image_extension=request.image_extension.value))
        add_mysql_rollback_callback(mysql_session=mysql_session, callback=lambda: client.delete_object(
            bucket_name=params.category_image_bucket, file_name=key))
        return MenuCategoryCreateResponse(menu_category_id=category.menu_category_id,
                                          name=category.name, display_order=category.display_order,
                                          is_active=category.is_active)
