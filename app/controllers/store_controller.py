from sqlalchemy.orm import Session

from app.middlewares.transaction import mysql_transaction
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.requests.store_manager_login_request import StoreManagerLoginRequest
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.requests.menu_create_request import MenuCreateRequest
from app.models.responses.store_manager_login_response import StoreManagerLoginResponse
from app.models.responses.menu_category_response import (
    MenuCategoryCreateResponse,
    MenuCategoryListResponse,
)
from app.models.responses.menu_create_response import MenuCreateResponse
from app.models.responses.menu_list_response import MenuListResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.services.store_service import StoreService
from app.models.responses.wallet_response import WalletResponse
from app.core.exceptions.message import (
    SERVER_ERROR,
    MENU_CATEGORY_IMAGE_INVALID_ERROR,
    MENU_CATEGORY_NOT_FOUND_ERROR,
    MENU_IMAGE_INVALID_ERROR,
    LOGIN_FAILED_ERROR,
    STORE_MANAGER_INACTIVE_ERROR,
    STORE_NOT_FOUND_ERROR,
    VERIFY_ERROR,
    WALLET_CONFLICT_ERROR,
    WALLET_IS_ALREADY_EXIST,
    WALLET_NOT_FOUND_ERROR,
)
from app.core.exceptions.custom_exception import (
    CustomHttpException,
    MenuCategoryImageInvalidException,
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
    StoreManagerInactiveException,
    StoreNotFoundException,
    UnauthorizedException,
    WalletConflictException,
    WalletNotFoundException,
)


class StoreController:
    """店舗ウォレット取得 API のリクエストを処理するコントローラーです。"""

    @mysql_transaction
    def login_store_manager(
        self,
        mysql_session: Session,
        request: StoreManagerLoginRequest,
    ) -> StoreManagerLoginResponse:
        """店舗管理者を認証し、アクセストークンを返す。

        Args:
            mysql_session: SQLAlchemy のセッション。
            request: メールアドレスとパスワードを含むログイン情報。

        Returns:
            JWTアクセストークンと店舗管理者情報。
        """
        try:
            return StoreService().login_store_manager(
                mysql_session=mysql_session,
                email=request.email,
                password=request.password,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=LOGIN_FAILED_ERROR,
            )
        except StoreManagerInactiveException:
            raise CustomHttpException.get_http_exception(
                status_code=403,
                message=STORE_MANAGER_INACTIVE_ERROR,
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            )

    @mysql_transaction
    def get_store_wallet(self, mysql_session: Session, store_id: int) -> WalletResponse | None:
        """リクエスト条件に一致する店舗ウォレットを取得します。

        Args:
            mysql_session: SQLAlchemy のセッションです。
            store_id: 取得対象の店舗 IDです。

        Returns:
            WalletResponse: 店舗ウォレットレスポンスです。
        """
        try:
            store_service = StoreService()
            return store_service.get_store_wallet(
                mysql_session=mysql_session,
                store_id=store_id
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def get_menu_categories(
        self,
        mysql_session: Session,
        store_id: int,
        name: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int | None = None,
    ) -> MenuCategoryListResponse:
        """認証済み管理者の店舗に紐づくメニューカテゴリーを取得する。

        Args:
            mysql_session: SQLAlchemy のセッションです。
            store_id: 取得対象の店舗 IDです。
            name: カテゴリー名の部分一致検索条件です。
            is_active: 有効状態の完全一致検索条件です。
            page: 取得するページ番号です。
            page_size: 1ページあたりの取得件数です。未指定時は全件取得します。

        Returns:
            MenuCategoryListResponse: カテゴリー一覧とページネーションです。
        """
        try:
            return StoreService().get_menu_categories(
                mysql_session=mysql_session,
                store_id=store_id,
                name=name,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            )

    @mysql_transaction
    def create_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        request: MenuCategoryCreateRequest,
    ) -> MenuCategoryCreateResponse:
        """認証済み管理者の店舗へメニューカテゴリーを登録する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 登録先店舗の ID。
            request: カテゴリー名、画像、表示順、有効状態を含む登録情報。

        Returns:
            登録したメニューカテゴリー情報。
        """
        try:
            return StoreService().create_menu_category(
                mysql_session=mysql_session,
                store_id=store_id,
                request=request,
            )
        except MenuCategoryImageInvalidException:
            raise CustomHttpException.get_http_exception(
                status_code=422,
                message=MENU_CATEGORY_IMAGE_INVALID_ERROR,
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            )

    @mysql_transaction
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
        """認証済み管理者の店舗に紐づくメニュー商品を取得する。

        Args:
            mysql_session: SQLAlchemy のセッションです。
            store_id: 取得対象の店舗 IDです。
            name: 商品名の部分一致検索条件です。
            menu_category_id: カテゴリー ID の完全一致検索条件です。
            is_available: 販売可能状態の完全一致検索条件です。
            page: 取得するページ番号です。
            page_size: 1ページあたりの取得件数です。

        Returns:
            MenuListResponse: 商品一覧とページネーションです。
        """
        try:
            return StoreService().get_menus(
                mysql_session=mysql_session,
                store_id=store_id,
                name=name,
                menu_category_id=menu_category_id,
                is_available=is_available,
                page=page,
                page_size=page_size,
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            )

    @mysql_transaction
    def create_menu(
        self,
        mysql_session: Session,
        store_id: int,
        request: MenuCreateRequest,
    ) -> MenuCreateResponse:
        """メニュー商品、オプショングループ、オプションを登録する。

        Args:
            mysql_session: SQLAlchemy のセッションです。
            store_id: 登録先店舗の IDです。
            request: メニュー登録情報です。

        Returns:
            MenuCreateResponse: 登録した各データのIDです。
        """
        try:
            return StoreService().create_menu(
                mysql_session=mysql_session,
                store_id=store_id,
                request=request,
            )
        except MenuCategoryNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=MENU_CATEGORY_NOT_FOUND_ERROR,
            )
        except MenuImageInvalidException:
            raise CustomHttpException.get_http_exception(
                status_code=422,
                message=MENU_IMAGE_INVALID_ERROR,
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            )

    @mysql_transaction
    def create_wallet_nonce(
        self,
        mysql_session: Session,
        store_id: int,
        request: WalletNonceCreateRequest,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名用の nonce を発行する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            request: nonce 発行に必要なウォレット情報。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        try:
            store_service = StoreService()
            return store_service.create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=request.wallet_address,
                chain_type=request.chain_type,
                network_name=request.network_name,
            )
        except StoreNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=STORE_NOT_FOUND_ERROR
            )

        except WalletConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=WALLET_IS_ALREADY_EXIST
            )

        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
    
    @mysql_transaction
    def verify_and_create_wallet_nonce(
        self,
        mysql_session: Session,
        store_id: int,
        request: WalletVerifyRequest) -> WalletVerifyResponse:
        """署名済み nonce を検証し、店舗ウォレットを作成する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            request: 店舗 ID、ウォレットアドレス、署名、チェーン種別、ネットワーク名を含む検証リクエスト。

        Returns:
            検証済みとして登録された店舗ウォレット情報。
        """
        try:
            store_service = StoreService()
            nonce_entity = store_service.verify_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=request.wallet_address,
                signature=request.signature,
                chain_type=request.chain_type,
                network_name=request.network_name
            )
            return store_service.create_store_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=request.wallet_address,
                chain_type=request.chain_type,
                network_name=request.network_name,
                token_symbol=request.token_symbol,
                chain_id=request.chain_id,
                nonce_entity=nonce_entity
            )
        except StoreNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=STORE_NOT_FOUND_ERROR
            )

        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=VERIFY_ERROR
            )
        
        except WalletConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=409,
                message=WALLET_CONFLICT_ERROR
            )
        
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def delete_wallet(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_id: int,
    ) -> None:
        """登録済みウォレットの削除を行う。
        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 認証済み管理者の店舗ID。
            wallet_id: ウォレットID。
        Returns:
            なし。
        """
        try:
            StoreService().delete_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_id=wallet_id
            )

        except WalletNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=WALLET_NOT_FOUND_ERROR,
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
