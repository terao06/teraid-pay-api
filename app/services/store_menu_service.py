"""店舗メニューのユースケースを提供するService。"""

from io import BytesIO
from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import (
    InvalidImageError,
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
    MenuItemNotFoundException,
)
from app.core.utils.image import ImageUtil
from app.helpers.image_replacement_helper import (
    ImageBucketType,
    ImageReplacementHelper,
)
from app.middlewares.transaction import add_mysql_rollback_callback
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.requests.menu_create_request import MenuCreateRequest
from app.models.requests.menu_update_request import MenuUpdateRequest
from app.models.responses.menu_create_response import MenuCreateResponse
from app.models.responses.menu_detail_response import (
    MenuDetailResponse,
    MenuOptionGroupResponse,
    MenuOptionResponse,
)
from app.models.responses.menu_list_response import MenuItemResponse, MenuListResponse, MenuPaginationResponse
from app.models.responses.menu_update_response import MenuUpdateResponse
from app.repositories.mysql.store_menu_repository import StoreMenuRepository


class StoreMenuService:
    """メニュー検索と、オプション・画像を含むメニュー登録を調整する。"""

    def get_menus(self, mysql_session: Session, store_id: int, name: str | None = None,
                  menu_category_id: int | None = None, is_available: bool | None = None,
                  page: int = 1, page_size: int = 20) -> MenuListResponse:
        """店舗のメニューを検索してカテゴリー名と画像URL付きで返す。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: メニュー名の部分一致条件。
            menu_category_id: カテゴリーIDの完全一致条件。
            is_available: 販売可能状態の完全一致条件。
            page: 取得するページ番号。
            page_size: 1ページの件数。

        Returns:
            メニュー一覧とページネーション情報。
        """
        repository = StoreMenuRepository()
        total = repository.count_menu_items(
            mysql_session=mysql_session, store_id=store_id, name=name,
            menu_category_id=menu_category_id, is_available=is_available)
        pagination = MenuPaginationResponse(page=page, page_size=page_size, total=total,
                                            total_pages=(total + page_size - 1) // page_size)
        if total == 0:
            return MenuListResponse(menu_items=[], pagination=pagination)
        items = repository.get_menu_items(
            mysql_session=mysql_session, store_id=store_id, name=name,
            menu_category_id=menu_category_id, is_available=is_available,
            offset=(page - 1) * page_size, limit=page_size)
        if not items:
            return MenuListResponse(menu_items=[], pagination=pagination)
        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        responses = []
        for item, category_name in items:
            key = f"{store_id}/{item.menu_item_id}.{item.image_extension}"
            responses.append(MenuItemResponse(
                menu_item_id=item.menu_item_id,
                menu_category_id=item.menu_category_id if category_name is not None else None,
                menu_category_name=category_name, name=item.name, description=item.description,
                price=f"{item.price:.6f}", token_symbol=item.token_symbol,
                image_url=client.generate_presigned_get_url(
                    bucket_name=params.menu_image_bucket, file_name=key,
                    expires_in=params.menu_image_url_expires_in),
                is_available=item.is_available, display_order=item.display_order))
        return MenuListResponse(menu_items=responses, pagination=pagination)

    def get_menu_detail(
        self,
        mysql_session: Session,
        store_id: int,
        menu_item_id: int,
    ) -> MenuDetailResponse:
        """店舗のメニュー商品をカテゴリーとオプション付きで取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 認証済み管理者の店舗ID。
            menu_item_id: 取得対象のメニュー商品ID。

        Returns:
            商品画像URL、カテゴリー、オプションを含むメニュー詳細。

        Raises:
            MenuItemNotFoundException: 対象商品が認証店舗に存在しない場合。
        """
        rows = StoreMenuRepository().get_menu_detail(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_item_id=menu_item_id,
        )
        if not rows:
            raise MenuItemNotFoundException("メニュー商品が存在しません。")

        item, category_name, _, _ = rows[0]
        grouped_options: dict[
            int,
            tuple[MenuOptionGroup, list[MenuOptionResponse]],
        ] = {}
        for _, _, option_group, option in rows:
            if option_group is None:
                continue
            group_data = grouped_options.get(option_group.menu_option_group_id)
            if group_data is None:
                group_data = (option_group, [])
                grouped_options[option_group.menu_option_group_id] = group_data
            if option is not None:
                group_data[1].append(
                    MenuOptionResponse(
                        menu_option_id=option.menu_option_id,
                        name=option.name,
                        additional_price=f"{option.additional_price:.6f}",
                        display_order=option.display_order,
                        is_available=option.is_available,
                    )
                )

        option_groups = [
            MenuOptionGroupResponse(
                menu_option_group_id=option_group.menu_option_group_id,
                name=option_group.name,
                min_selections=option_group.min_selections,
                max_selections=option_group.max_selections,
                display_order=option_group.display_order,
                is_active=option_group.is_active,
                options=options,
            )
            for option_group, options in grouped_options.values()
        ]
        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        key = f"{store_id}/{item.menu_item_id}.{item.image_extension}"
        return MenuDetailResponse(
            menu_item_id=item.menu_item_id,
            menu_category_id=(
                item.menu_category_id if category_name is not None else None
            ),
            menu_category_name=category_name,
            name=item.name,
            description=item.description,
            price=f"{item.price:.6f}",
            token_symbol=item.token_symbol,
            image_url=client.generate_presigned_get_url(
                bucket_name=params.menu_image_bucket,
                file_name=key,
                expires_in=params.menu_image_url_expires_in,
            ),
            is_available=item.is_available,
            display_order=item.display_order,
            option_groups=option_groups,
        )

    def update_menu(
        self,
        mysql_session: Session,
        store_id: int,
        menu_item_id: int,
        request: MenuUpdateRequest,
    ) -> MenuUpdateResponse:
        """店舗に属するメニュー商品の基本情報と任意の画像を更新する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 認証済み管理者の店舗ID。
            menu_item_id: 更新対象のメニュー商品ID。
            request: 更新後の商品基本情報と任意の画像。

        Returns:
            更新したメニュー商品ID。

        Raises:
            MenuItemNotFoundException: 対象商品が認証店舗に存在しない場合。
            MenuCategoryNotFoundException: 指定カテゴリーを利用できない場合。
            MenuImageInvalidException: 差し替え画像を読み込めない場合。
        """
        repository = StoreMenuRepository()
        item = repository.get_menu_item_for_update(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_item_id=menu_item_id,
        )
        if item is None:
            raise MenuItemNotFoundException("メニュー商品が存在しません。")
        if (
            request.menu_category_id is not None
            and repository.get_active_menu_category(
                mysql_session=mysql_session,
                store_id=store_id,
                menu_category_id=request.menu_category_id,
            )
            is None
        ):
            raise MenuCategoryNotFoundException(
                "指定されたメニューカテゴリーは利用できません。"
            )

        if request.menu_image is not None and request.image_extension is not None:
            old_extension = item.image_extension
            old_key = f"{store_id}/{item.menu_item_id}.{old_extension}"
            new_key = (
                f"{store_id}/{item.menu_item_id}.{request.image_extension.value}"
            )
            try:
                ImageReplacementHelper().replace_image(
                    mysql_session=mysql_session,
                    image_content=request.menu_image,
                    old_key=old_key,
                    new_key=new_key,
                    old_extension=old_extension,
                    new_extension=request.image_extension.value,
                    image_bucket_type=ImageBucketType.MENU,
                )
            except InvalidImageError as exc:
                raise MenuImageInvalidException(
                    "メニュー画像を読み込めません。"
                ) from exc
            item.image_extension = request.image_extension.value

        item.menu_category_id = request.menu_category_id
        item.name = request.name
        item.description = request.description
        item.price = request.price
        item.token_symbol = request.token_symbol
        item.is_available = request.is_available
        item.display_order = request.display_order
        updated_item = repository.update_menu_item(
            mysql_session=mysql_session,
            menu_item=item,
        )
        return MenuUpdateResponse(
            menu_item_id=updated_item.menu_item_id,
        )

    def create_menu(self, mysql_session: Session, store_id: int,
                    request: MenuCreateRequest) -> MenuCreateResponse:
        """メニュー、オプショングループ、オプション、画像を登録する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 登録先店舗ID。
            request: メニューとオプション構成を含む登録リクエスト。

        Returns:
            登録されたメニューID。

        Raises:
            MenuImageInvalidException: Base64画像をデコードできない場合。
            MenuCategoryNotFoundException: 指定カテゴリーが利用できない場合。
        """
        try:
            image_bytes = ImageUtil.decode_base64_image(
                content=request.menu_image, image_extension=request.image_extension.value)
        except ValueError as exc:
            raise MenuImageInvalidException("メニュー画像を読み込めません。") from exc
        repository = StoreMenuRepository()
        if request.menu_category_id is not None and repository.get_active_menu_category(
                mysql_session=mysql_session, store_id=store_id,
                menu_category_id=request.menu_category_id) is None:
            raise MenuCategoryNotFoundException("指定されたメニューカテゴリーは利用できません。")
        item = repository.create_menu_item(mysql_session=mysql_session, menu_item=MenuItem(
            store_id=store_id, menu_category_id=request.menu_category_id, name=request.name,
            description=request.description, price=request.price, token_symbol=request.token_symbol,
            image_extension=request.image_extension.value, is_available=request.is_available,
            display_order=request.display_order))
        for group_request in request.option_groups:
            group = repository.create_menu_option_group(
                mysql_session=mysql_session, menu_option_group=MenuOptionGroup(
                menu_item_id=item.menu_item_id, name=group_request.name,
                min_selections=group_request.min_selections, max_selections=group_request.max_selections,
                display_order=group_request.display_order, is_active=group_request.is_active))
            for option_request in group_request.options:
                repository.create_menu_option(
                    mysql_session=mysql_session, menu_option=MenuOption(
                    menu_option_group_id=group.menu_option_group_id, name=option_request.name,
                    additional_price=option_request.additional_price,
                    display_order=option_request.display_order, is_available=option_request.is_available))
        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        key = f"{store_id}/{item.menu_item_id}.{request.image_extension.value}"
        client.upload_object(bucket_name=params.menu_image_bucket, file=BytesIO(image_bytes),
                             file_name=key, content_type=ImageUtil.get_content_type(
                                 image_extension=request.image_extension.value))
        add_mysql_rollback_callback(mysql_session=mysql_session, callback=lambda: client.delete_object(
            bucket_name=params.menu_image_bucket, file_name=key))
        return MenuCreateResponse(menu_item_id=item.menu_item_id)
