"""店舗メニューカテゴリーのユースケースを提供するService。"""

from io import BytesIO

from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import (
    InvalidImageError,
    MenuCategoryImageInvalidException,
    MenuCategoryNotFoundException,
)
from app.core.utils.image import ImageUtil
from app.helpers.image_replacement_helper import (
    ImageBucketType,
    ImageReplacementHelper,
)
from app.middlewares.transaction import add_mysql_rollback_callback
from app.models.mysql.menu_category import MenuCategory
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.requests.menu_category_update_request import MenuCategoryUpdateRequest
from app.models.responses.menu_category_response import (
    MenuCategoryCreateResponse,
    MenuCategoryDeleteResponse,
    MenuCategoryListResponse,
    MenuCategoryPaginationResponse,
    MenuCategoryResponse,
    MenuCategoryUpdateResponse,
)
from app.repositories.mysql.store_menu_category_repository import StoreMenuCategoryRepository


class StoreMenuCategoryService:
    """カテゴリーの検索、登録、更新、削除と画像保存を調整する。"""

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
        """認証店舗の未削除カテゴリーを排他ロックして更新する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 更新対象の店舗ID。
            menu_category_id: 更新対象のメニューカテゴリーID。
            request: カテゴリー名、任意の画像、表示順、有効状態を含む更新情報。

        Returns:
            更新したメニューカテゴリーID。

        Raises:
            MenuCategoryNotFoundException: 対象カテゴリーが存在しない場合。
            MenuCategoryImageInvalidException: 更新画像を読み込めない場合。
        """
        repository = StoreMenuCategoryRepository()
        category = repository.get_menu_category_detail(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
            lock_for_update=True,
        )
        if category is None:
            raise MenuCategoryNotFoundException(
                "メニューカテゴリーが存在しません。"
            )

        if request.category_image is not None and request.image_extension is not None:
            old_extension = category.image_extension
            old_key = f"{store_id}/{category.menu_category_id}.{old_extension}"
            new_key = (
                f"{store_id}/{category.menu_category_id}."
                f"{request.image_extension.value}"
            )
            try:
                ImageReplacementHelper().replace_image(
                    mysql_session=mysql_session,
                    image_content=request.category_image,
                    old_key=old_key,
                    new_key=new_key,
                    old_extension=old_extension,
                    new_extension=request.image_extension.value,
                    image_bucket_type=ImageBucketType.CATEGORY,
                )
            except InvalidImageError as exc:
                raise MenuCategoryImageInvalidException(
                    "カテゴリー画像を読み込めません。"
                ) from exc
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
        )

    def delete_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
    ) -> MenuCategoryDeleteResponse:
        """認証店舗の未削除カテゴリーを排他ロックして論理削除する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            menu_category_id: 削除対象のメニューカテゴリーID。

        Returns:
            削除したメニューカテゴリーIDを含むレスポンス。

        Raises:
            MenuCategoryNotFoundException: 対象が存在しない、削除済み、または別店舗に属する場合。
        """
        repository = StoreMenuCategoryRepository()
        category = repository.get_menu_category_detail(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
            lock_for_update=True,
        )
        if category is None:
            raise MenuCategoryNotFoundException()

        repository.soft_delete_menu_category(
            mysql_session=mysql_session,
            menu_category=category,
        )
        return MenuCategoryDeleteResponse(menu_category_id=category.menu_category_id)

    def create_menu_category(self, mysql_session: Session, store_id: int,
                             request: MenuCategoryCreateRequest) -> MenuCategoryCreateResponse:
        """メニューカテゴリーとカテゴリー画像を登録する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 登録先店舗ID。
            request: カテゴリー名、画像、表示順、有効状態を含む登録リクエスト。

        Returns:
            登録したメニューカテゴリーID。

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
        return MenuCategoryCreateResponse(menu_category_id=category.menu_category_id)
