from datetime import datetime, timedelta
from io import BytesIO
import secrets

from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    MenuCategoryImageInvalidException,
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
    StoreManagerInactiveException,
    StoreNotFoundException,
    WalletNotFoundException,
    WalletConflictException,
    UnauthorizedException
)
from app.core.config.store_manager_auth import get_store_manager_auth_config
from app.core.utils.store_manager_auth import StoreManagerAuthUtil
from app.core.utils.datetime import DateTimeUtil
from app.core.utils.logging import TeraidPayApiLog
from app.core.utils.wallet import WalletUtil
from app.core.utils.image import ImageUtil
from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.middlewares.transaction import add_mysql_rollback_callback
from app.models.mysql.nonce import Nonce
from app.models.mysql.menu_category import MenuCategory
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_nonce import StoreNonce
from app.models.mysql.wallet import Wallet
from app.models.responses.wallet_response import WalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)
from app.models.responses.menu_category_response import (
    MenuCategoryCreateResponse,
    MenuCategoryListResponse,
    MenuCategoryPaginationResponse,
    MenuCategoryResponse,
)
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.requests.menu_create_request import MenuCreateRequest
from app.models.responses.menu_create_response import (
    MenuCreateResponse,
    MenuOptionGroupCreateResponse,
)
from app.models.responses.menu_list_response import (
    MenuItemResponse,
    MenuListResponse,
    MenuPaginationResponse,
)
from app.repositories.mysql.nonce_repository import NonceRepository
from app.repositories.mysql.store_repository import StoreRepository
from app.core.utils.datetime import JST
from app.repositories.mysql.wallet_repository import WalletRepository


class StoreService:
    """店舗ウォレット関連処理を担当するサービス。"""

    def login_store_manager(
        self,
        mysql_session: Session,
        email: str,
        password: str,
    ) -> StoreManagerLoginResponse:
        """店舗管理者を認証し、JWTアクセストークンを発行する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            email: 店舗管理者のメールアドレス。
            password: 店舗管理者のパスワード。

        Returns:
            JWTアクセストークンと店舗管理者情報。
        """
        normalized_email = email.strip().lower()
        store_manager = StoreRepository().get_store_manager_by_email(
            mysql_session=mysql_session,
            email=normalized_email,
        )

        if store_manager is None:
            # NOTE: 管理者が存在する場合と応答時間を近づけ、メールアドレス列挙攻撃を防ぐためダミー照合を行う。
            StoreManagerAuthUtil.perform_dummy_password_check(password)
            raise UnauthorizedException("店舗管理者の認証に失敗しました。")

        if not StoreManagerAuthUtil.verify_password(
            password=password,
            password_hash=store_manager.password_hash,
        ):
            raise UnauthorizedException("店舗管理者の認証に失敗しました。")

        if not store_manager.is_active:
            raise StoreManagerInactiveException(
                "店舗管理者アカウントが無効です。"
            )

        auth_config = get_store_manager_auth_config()
        access_token = StoreManagerAuthUtil.create_access_token(
            store_manager=store_manager,
            config=auth_config,
        )
        return StoreManagerLoginResponse(
            access_token=access_token,
            expires_in=auth_config.access_token_expire_seconds,
            store_manager=StoreManagerInfoResponse(
                store_manager_id=store_manager.store_manager_id,
                store_id=store_manager.store_id,
                name=store_manager.name,
                roll_id=store_manager.roll_id,
            ),
        )

    def get_store_wallet(self, mysql_session: Session, store_id: int) -> WalletResponse | None:
        """店舗 ID に紐づくウォレット情報を取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            店舗ウォレットのレスポンス。存在しない場合は None。
        """
        wallet_info = StoreRepository().get_store_wallet(
            mysql_session=mysql_session,
            store_id=store_id
        )

        if wallet_info is None:
            return None

        return WalletResponse(
            wallet_id=wallet_info.wallet_id,
            wallet_address=wallet_info.wallet_address,
            chain_type=wallet_info.chain_type,
            network_name=wallet_info.network_name,
            token_symbol=wallet_info.token_symbol,
            chain_id=wallet_info.chain_id,
            is_active=wallet_info.is_active,
            is_permitted=wallet_info.is_permitted,
            verified_at=DateTimeUtil.change_datetime_to_string(wallet_info.verified_at),
            created_at=DateTimeUtil.change_datetime_to_string(wallet_info.created_at),
            updated_at=DateTimeUtil.change_datetime_to_string(wallet_info.updated_at)
        )

    def get_menu_categories(
        self,
        mysql_session: Session,
        store_id: int,
        name: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int | None = None,
    ) -> MenuCategoryListResponse:
        """店舗に紐づくメニューカテゴリーを検索してページ単位で取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            name: カテゴリー名の部分一致検索条件。
            is_active: 有効状態の完全一致検索条件。
            page: 取得するページ番号。
            page_size: 1ページあたりの取得件数。未指定時は全件取得する。

        Returns:
            カテゴリー一覧、画像URL、ページネーションを含むレスポンス。
        """
        repository = StoreRepository()
        total = repository.count_menu_categories(
            mysql_session=mysql_session,
            store_id=store_id,
            name=name,
            is_active=is_active,
        )
        pagination_enabled = page_size is not None
        response_page = page if pagination_enabled else 1
        total_pages = (
            (total + page_size - 1) // page_size
            if page_size is not None
            else (1 if total > 0 else 0)
        )
        pagination = MenuCategoryPaginationResponse(
            page=response_page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
        if total == 0:
            return MenuCategoryListResponse(
                menu_categories=[],
                pagination=pagination,
            )

        menu_categories = repository.get_menu_categories(
            mysql_session=mysql_session,
            store_id=store_id,
            name=name,
            is_active=is_active,
            offset=(page - 1) * page_size if page_size is not None else 0,
            limit=page_size,
        )
        if not menu_categories:
            return MenuCategoryListResponse(
                menu_categories=[],
                pagination=pagination,
            )

        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        menu_category_responses = []
        for menu_category in menu_categories:
            image_object_key = (
                f"{store_id}/{menu_category.menu_category_id}."
                f"{menu_category.image_extension}"
            )
            image_url = s3_client.generate_presigned_get_url(
                bucket_name=ssm_params.category_image_bucket,
                file_name=image_object_key,
                expires_in=ssm_params.menu_image_url_expires_in,
            )
            menu_category_responses.append(
                MenuCategoryResponse(
                    menu_category_id=menu_category.menu_category_id,
                    name=menu_category.name,
                    image_url=image_url,
                    display_order=menu_category.display_order,
                    is_active=menu_category.is_active,
                )
            )

        return MenuCategoryListResponse(
            menu_categories=menu_category_responses,
            pagination=pagination,
        )

    def create_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        request: MenuCategoryCreateRequest,
    ) -> MenuCategoryCreateResponse:
        """店舗に紐づくメニューカテゴリーとカテゴリー画像を登録する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 登録先店舗の ID。
            request: カテゴリー名、画像、表示順、有効状態を含む登録情報。

        Returns:
            登録したカテゴリーの ID、名称、表示順、有効状態。
        """
        try:
            category_image_bytes = ImageUtil.decode_base64_image(
                content=request.category_image,
                image_extension=request.image_extension.value,
            )
        except ValueError as exc:
            raise MenuCategoryImageInvalidException(
                "カテゴリー画像を読み込めません。"
            ) from exc

        store_repository = StoreRepository()
        menu_category = MenuCategory(
            store_id=store_id,
            name=request.name,
            image_extension=request.image_extension.value,
            display_order=request.display_order,
            is_active=request.is_active,
        )
        saved_menu_category = store_repository.create_menu_category(
            mysql_session=mysql_session,
            menu_category=menu_category,
        )

        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        image_object_key = (
            f"{store_id}/{saved_menu_category.menu_category_id}."
            f"{request.image_extension.value}"
        )
        s3_client.upload_object(
            bucket_name=ssm_params.category_image_bucket,
            file=BytesIO(category_image_bytes),
            file_name=image_object_key,
            content_type=ImageUtil.get_content_type(
                image_extension=request.image_extension.value
            ),
        )
        add_mysql_rollback_callback(
            mysql_session=mysql_session,
            callback=lambda: s3_client.delete_object(
                bucket_name=ssm_params.category_image_bucket,
                file_name=image_object_key,
            ),
        )

        return MenuCategoryCreateResponse(
            menu_category_id=saved_menu_category.menu_category_id,
            name=saved_menu_category.name,
            display_order=saved_menu_category.display_order,
            is_active=saved_menu_category.is_active,
        )

    def get_menus(
        self,
        mysql_session: Session,
        store_id: int,
        name: str | None = None,
        menu_category_id: int | None = None,
        is_available: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MenuListResponse:
        """店舗に紐づく未削除のメニュー商品一覧を取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            name: 商品名の部分一致検索条件。
            menu_category_id: カテゴリー ID の完全一致検索条件。
            is_available: 販売可能状態の完全一致検索条件。
            page: 取得するページ番号。
            page_size: 1ページあたりの取得件数。

        Returns:
            商品一覧、画像URL、ページネーションを含むレスポンス。
        """
        repository = StoreRepository()
        total = repository.count_menu_items(
            mysql_session=mysql_session,
            store_id=store_id,
            name=name,
            menu_category_id=menu_category_id,
            is_available=is_available,
        )
        total_pages = (total + page_size - 1) // page_size
        pagination = MenuPaginationResponse(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
        if total == 0:
            return MenuListResponse(menu_items=[], pagination=pagination)

        menu_items = repository.get_menu_items(
            mysql_session=mysql_session,
            store_id=store_id,
            name=name,
            menu_category_id=menu_category_id,
            is_available=is_available,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        if not menu_items:
            return MenuListResponse(menu_items=[], pagination=pagination)

        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        menu_item_responses = []
        for menu_item, menu_category_name in menu_items:
            image_object_key = (
                f"{store_id}/{menu_item.menu_item_id}."
                f"{menu_item.image_extension}"
            )
            image_url = s3_client.generate_presigned_get_url(
                bucket_name=ssm_params.menu_image_bucket,
                file_name=image_object_key,
                expires_in=ssm_params.menu_image_url_expires_in,
            )
            menu_item_responses.append(
                MenuItemResponse(
                    menu_item_id=menu_item.menu_item_id,
                    menu_category_id=(
                        menu_item.menu_category_id
                        if menu_category_name is not None
                        else None
                    ),
                    menu_category_name=menu_category_name,
                    name=menu_item.name,
                    description=menu_item.description,
                    price=f"{menu_item.price:.6f}",
                    token_symbol=menu_item.token_symbol,
                    image_url=image_url,
                    is_available=menu_item.is_available,
                    display_order=menu_item.display_order,
                )
            )

        return MenuListResponse(
            menu_items=menu_item_responses,
            pagination=pagination,
        )

    def create_menu(
        self,
        mysql_session: Session,
        store_id: int,
        request: MenuCreateRequest,
    ) -> MenuCreateResponse:
        """メニュー商品、オプショングループ、オプションを登録する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 登録先店舗の ID。
            request: メニュー登録情報。

        Returns:
            登録した商品、オプショングループ、オプションのID。
        """
        try:
            menu_image_bytes = ImageUtil.decode_base64_image(
                content=request.menu_image,
                image_extension=request.image_extension.value,
            )
        except ValueError as exc:
            raise MenuImageInvalidException(
                "メニュー画像を読み込めません。"
            ) from exc
        store_repository = StoreRepository()

        if request.menu_category_id is not None:
            menu_category = store_repository.get_active_menu_category(
                mysql_session=mysql_session,
                store_id=store_id,
                menu_category_id=request.menu_category_id,
            )
            if menu_category is None:
                raise MenuCategoryNotFoundException(
                    "指定されたメニューカテゴリーは利用できません。"
                )

        menu_item = MenuItem(
            store_id=store_id,
            menu_category_id=request.menu_category_id,
            name=request.name,
            description=request.description,
            price=request.price,
            token_symbol=request.token_symbol,
            image_extension=request.image_extension.value,
            is_available=request.is_available,
            display_order=request.display_order,
        )
        saved_menu_item = store_repository.create_menu_item(
            mysql_session=mysql_session,
            menu_item=menu_item,
        )

        menu_option_group_responses = []
        for option_group_request in request.option_groups:
            menu_option_group = MenuOptionGroup(
                menu_item_id=saved_menu_item.menu_item_id,
                name=option_group_request.name,
                min_selections=option_group_request.min_selections,
                max_selections=option_group_request.max_selections,
                display_order=option_group_request.display_order,
                is_active=option_group_request.is_active,
            )
            saved_menu_option_group = store_repository.create_menu_option_group(
                mysql_session=mysql_session,
                menu_option_group=menu_option_group,
            )

            menu_option_ids = []
            for option_request in option_group_request.options:
                menu_option = MenuOption(
                    menu_option_group_id=(
                        saved_menu_option_group.menu_option_group_id
                    ),
                    name=option_request.name,
                    additional_price=option_request.additional_price,
                    display_order=option_request.display_order,
                    is_available=option_request.is_available,
                )
                saved_menu_option = store_repository.create_menu_option(
                    mysql_session=mysql_session,
                    menu_option=menu_option,
                )
                menu_option_ids.append(saved_menu_option.menu_option_id)

            menu_option_group_responses.append(
                MenuOptionGroupCreateResponse(
                    menu_option_group_id=(
                        saved_menu_option_group.menu_option_group_id
                    ),
                    menu_option_ids=menu_option_ids,
                )
            )

        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        image_object_key = (
            f"{store_id}/{saved_menu_item.menu_item_id}."
            f"{request.image_extension.value}"
        )
        s3_client.upload_object(
            bucket_name=ssm_params.menu_image_bucket,
            file=BytesIO(menu_image_bytes),
            file_name=image_object_key,
            content_type=ImageUtil.get_content_type(
                image_extension=request.image_extension.value
            ),
        )
        add_mysql_rollback_callback(
            mysql_session=mysql_session,
            callback=lambda: s3_client.delete_object(
                bucket_name=ssm_params.menu_image_bucket,
                file_name=image_object_key,
            ),
        )

        return MenuCreateResponse(
            menu_item_id=saved_menu_item.menu_item_id,
            menu_option_groups=menu_option_group_responses,
        )


    def create_wallet_nonce(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名に使用する nonce を生成する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        store_repository = StoreRepository()
        nonce_repository = NonceRepository()
        wallet_repository = WalletRepository()

        store = store_repository.get_store_by_id(
            mysql_session=mysql_session,
            store_id=store_id
        )
        if not store:
            raise StoreNotFoundException(f"対象の店舗は存在しません. store_id={store_id}")
        
        exist_wallet = wallet_repository.get_wallet_by_address(
            mysql_session=mysql_session,
            wallet_address=wallet_address)

        if exist_wallet is not None:
            raise WalletConflictException("このウォレットは既に使用されています。")

        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)
        now = datetime.now(JST)
        expires_at = now + timedelta(minutes=10)
        nonce_str = secrets.token_urlsafe(32)
        nonce = Nonce(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            nonce=nonce_str,
            expires_at=expires_at,
        )
        saved_nonce = nonce_repository.create_nonce(mysql_session=mysql_session, nonce=nonce)
        
        store_nonce = StoreNonce(
            store_id=store_id,
            nonce_id=saved_nonce.nonce_id
        )
        store_repository.create_store_nonce(
            mysql_session=mysql_session,
            store_nonce=store_nonce
        )

        return WalletNonceCreateResponse(
            nonce=nonce_str,
            expires_at=DateTimeUtil.change_datetime_to_string(expires_at)
        )

    def verify_wallet_nonce(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_address: str,
        signature: str,
        chain_type: str,
        network_name: str) -> Nonce:
        """署名済み nonce を検証し、利用可能な nonce エンティティを返す。
        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 検証対象のウォレットアドレス。
            signature: 署名文字列。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
        Returns:
            検証に成功した未使用の Nonce。
        """
        store_repository = StoreRepository()

        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)
        store = store_repository.get_store_by_id(mysql_session=mysql_session, store_id=store_id)
        if store is None:
            raise StoreNotFoundException(f"対象の店舗は存在しません. store_id={store_id}")

        stor_nonce_entity = store_repository.get_latest_available_nonce(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            expires_at=datetime.now()
        )

        if stor_nonce_entity is None:
            raise UnauthorizedException(
                '有効なnonceが見つかりません。',
            )

        recovered_address = WalletUtil.recover_address(
            message=stor_nonce_entity.nonce,
            signature=signature,
        )

        if recovered_address.lower() != normalized_wallet_address:
            raise UnauthorizedException("認証に失敗しました。")
        return stor_nonce_entity

    def create_store_wallet(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        token_symbol: str,
        chain_id: int,
        nonce_entity: Nonce) -> WalletVerifyResponse:
        """店舗ウォレットを登録する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 登録対象のウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            token_symbol: ウォレットで利用するトークンシンボル。
            chain_id: 対象ネットワークのチェーン ID。
            nonce_entity: 検証済みの nonce エンティティ。

        Returns:
            WalletVerifyResponse: ウォレット検証レスポンス。
        """

        store_repository = StoreRepository()
        wallet_repository = WalletRepository()
        nonce_repository = NonceRepository()

        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)

        existing_wallet = store_repository.get_wallet_by_store_id(
            mysql_session=mysql_session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )
        if existing_wallet is not None:
            TeraidPayApiLog.warning(
                f"この店舗にはすでにウォレットが登録されています。wallet_id={existing_wallet.wallet_id}")
            raise WalletConflictException(
                f"この店舗にはすでにウォレットが登録されています。wallet_id={existing_wallet.wallet_id}")

        new_wallet = Wallet(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            token_symbol=token_symbol,
            chain_id=chain_id,
            verified_at=datetime.now(),
            is_active=True,
            is_permitted=True,
        )
        saved_wallet = wallet_repository.create_wallet(
            mysql_session=mysql_session,
            wallet=new_wallet
        )

        new_store_wallet = StoreWallet(
            store_id=store_id,
            wallet_id=saved_wallet.wallet_id
        )
        store_repository.create_store_wallet(
            mysql_session=mysql_session,
            store_wallet=new_store_wallet)

        nonce_entity.used_at = datetime.now()
        nonce_repository.update_nonce(
            mysql_session=mysql_session,
            nonce=nonce_entity
        )
        store_repository.delete_store_nonce_by_nonce_id(
            mysql_session=mysql_session,
            nonce_id=nonce_entity.nonce_id
        )

        return WalletVerifyResponse(
            wallet_address=new_wallet.wallet_address,
            chain_type=new_wallet.chain_type,
            network_name=new_wallet.network_name,
            token_symbol=new_wallet.token_symbol,
            chain_id=new_wallet.chain_id,
            is_active=bool(new_wallet.is_active),
            is_permitted=bool(new_wallet.is_permitted),
            verified_at=DateTimeUtil.change_datetime_to_string(
                new_wallet.verified_at
            ),
        )

    def delete_wallet(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_id: int,
    ) -> None:
        """ウォレットを登録から削除する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 認証済み管理者の店舗ID。
            wallet_id: 削除対象のウォレットID。

        Returns:
            なし。
        """
        store_repository = StoreRepository()
        store_wallet = store_repository.get_store_wallet_link(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )
        if store_wallet is None:
            raise WalletNotFoundException(
                f"店舗に紐づくウォレットが存在しません。store_id={store_id} wallet_id={wallet_id}"
            )

        WalletRepository().delete_wallet_by_wallet_id(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        store_repository.delete_store_wallet_by_wallet_id(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
