"""店舗管理者向けAPIのルーティングを提供する。"""

from fastapi import APIRouter, Depends, Path, Query, Response
from app.controllers.store_controller import StoreController
from app.dependencies.store_manager_auth import (
    StoreManagerAuthContext,
    StoreManagerTokenClaims,
    authenticate_store_manager,
    get_store_manager_token_claims,
)
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.requests.device_create_request import DeviceCreateRequest
from app.models.requests.device_update_request import DeviceUpdateRequest
from app.models.requests.store_manager_login_request import StoreManagerLoginRequest
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.requests.menu_category_update_request import MenuCategoryUpdateRequest
from app.models.requests.menu_create_request import MenuCreateRequest
from app.models.requests.menu_option_groups_update_request import (
    MenuOptionGroupsUpdateRequest,
)
from app.models.requests.menu_update_request import MenuUpdateRequest
from app.core.utils.logging import TeraidPayApiLog

store_router = APIRouter()


@store_router.post("/manager/login")
@response_rapper()
@request_rapper()
def login_store_manager(request: StoreManagerLoginRequest):
    """店舗管理者をメールアドレスとパスワードで認証する。

    Args:
        request: メールアドレスとパスワードを含むログイン情報。

    Returns:
        JWTアクセストークンと店舗管理者情報を含む共通レスポンス。
    """
    return StoreController().login_store_manager(request=request)


@store_router.post("/manager/logout", status_code=204, response_class=Response)
def logout_store_manager(
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
    claims: StoreManagerTokenClaims = Depends(get_store_manager_token_claims),
) -> Response:
    """リクエストの認証に使用したアクセストークンを失効する。

    Args:
        auth_context: DB上の状態を確認済みの店舗管理者情報。
        claims: 検証済みのJWTクレーム。

    Returns:
        失効の確定を示す、本文なしの204レスポンス。

    Raises:
        HTTPException: JWTを認証できないか、DBへの失効登録に失敗した場合。
    """
    StoreController().logout_store_manager(
        jti=claims.jti,
        store_manager_id=auth_context.store_manager_id,
        expires_at=claims.expires_at,
    )
    return Response(status_code=204)


@store_router.post("/devices", status_code=201)
@response_rapper()
@request_rapper()
def create_device(
    request: DeviceCreateRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗へデバイスを登録する。

    Args:
        request: デバイス名を含む登録リクエスト。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        登録したデバイスIDを含む共通レスポンス。
    """
    return StoreController().create_device(
        store_id=auth_context.store_id,
        request=request,
    )


@store_router.get("/devices")
@response_rapper()
@request_rapper()
def get_devices(
    device_name: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に紐づくデバイス一覧を取得する。

    Args:
        device_name: デバイス名の部分一致条件。
        is_active: 利用可能状態の完全一致条件。
        page: 取得するページ番号。
        page_size: 1ページあたりの取得件数。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        デバイス一覧とページネーション情報を含む共通レスポンス。
    """
    return StoreController().get_devices(
        store_id=auth_context.store_id,
        device_name=device_name,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@store_router.get("/devices/{device_id}")
@response_rapper()
@request_rapper()
def get_device_detail(
    device_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するデバイス詳細を取得する。

    Args:
        device_id: 取得対象のデバイスID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        管理画面へ表示可能なデバイス詳細情報を含む共通レスポンス。
    """
    return StoreController().get_device_detail(
        store_id=auth_context.store_id,
        device_id=device_id,
    )


@store_router.put("/devices/{device_id}")
@response_rapper()
@request_rapper()
def update_device(
    request: DeviceUpdateRequest,
    device_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するデバイスを更新する。

    Args:
        request: デバイス名または利用状態を含む更新リクエスト。
        device_id: 更新対象のデバイスID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        更新したデバイスIDを含む共通レスポンス。
    """
    return StoreController().update_device(
        store_id=auth_context.store_id,
        device_id=device_id,
        request=request,
    )


@store_router.post("/devices/{device_id}/activation-code")
@response_rapper()
@request_rapper()
def issue_device_activation_code(
    response: Response,
    device_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """未有効化デバイスへ新しい有効化コードを発行する。

    Args:
        response: キャッシュ禁止ヘッダーを設定するHTTPレスポンス。
        device_id: 有効化コードを発行するデバイスID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        平文の有効化コードと有効期限を含む共通レスポンス。
    """
    response.headers["Cache-Control"] = "no-store"
    return StoreController().issue_device_activation_code(
        store_id=auth_context.store_id,
        device_id=device_id,
    )


@store_router.delete("/devices/{device_id}")
@response_rapper()
@request_rapper()
def delete_device(
    device_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するデバイスを論理削除する。

    Args:
        device_id: 削除対象のデバイスID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        削除したデバイスIDを含む共通レスポンス。
    """
    return StoreController().delete_device(
        store_id=auth_context.store_id,
        device_id=device_id,
    )


@store_router.get("/wallet")
@response_rapper()
@request_rapper()
def get_wallet_nonce(
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """店舗のウォレット情報を取得する。

    Args:
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        共通レスポンス形式で整形されるウォレット情報。
    """
    return StoreController().get_store_wallet(store_id=auth_context.store_id)


@store_router.get("/menu/categories")
@response_rapper()
@request_rapper()
def get_menu_categories(
    name: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に紐づくメニューカテゴリーを検索する。

    Args:
        name: カテゴリー名の部分一致検索条件。
        is_active: 有効状態の完全一致検索条件。
        page: 取得するページ番号。
        page_size: 1ページあたりの取得件数。未指定時は全件取得する。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        カテゴリー一覧とページネーションを含む共通レスポンス。
    """
    return StoreController().get_menu_categories(
        store_id=auth_context.store_id,
        name=name,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@store_router.get("/menu/categories/{menu_category_id}")
@response_rapper()
@request_rapper()
def get_menu_category_detail(
    menu_category_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するメニューカテゴリー詳細を取得する。

    Args:
        menu_category_id: 取得対象のメニューカテゴリーID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        カテゴリー詳細を含む共通レスポンス。
    """
    return StoreController().get_menu_category_detail(
        store_id=auth_context.store_id,
        menu_category_id=menu_category_id,
    )


@store_router.put("/menu/categories/{menu_category_id}")
@response_rapper()
@request_rapper()
def update_menu_category(
    request: MenuCategoryUpdateRequest,
    menu_category_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するメニューカテゴリーを更新する。

    Args:
        request: カテゴリー名、任意の画像、表示順、有効状態を含む更新情報。
        menu_category_id: 更新対象のメニューカテゴリーID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        更新したメニューカテゴリーIDを含む共通レスポンス。
    """
    return StoreController().update_menu_category(
        store_id=auth_context.store_id,
        menu_category_id=menu_category_id,
        request=request,
    )


@store_router.post("/menu/categories", status_code=201)
@response_rapper()
@request_rapper()
def create_menu_category(
    request: MenuCategoryCreateRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗へ画像付きメニューカテゴリーを登録する。

    Args:
        request: カテゴリー名、画像、表示順、有効状態を含む登録情報。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        登録したメニューカテゴリーIDを含む共通レスポンス。
    """
    return StoreController().create_menu_category(
        store_id=auth_context.store_id,
        request=request,
    )


@store_router.get("/menu")
@response_rapper()
@request_rapper()
def get_menus(
    name: str | None = Query(default=None, min_length=1, max_length=255),
    menu_category_id: int | None = Query(default=None, ge=1),
    is_available: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に紐づくメニュー商品を取得する。

    Args:
        name: 商品名の部分一致検索条件。
        menu_category_id: カテゴリー ID の完全一致検索条件。
        is_available: 販売可能状態の完全一致検索条件。
        page: 取得するページ番号。
        page_size: 1ページあたりの取得件数。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        商品一覧とページネーションを含む共通レスポンス。
    """
    return StoreController().get_menus(
        store_id=auth_context.store_id,
        name=name,
        menu_category_id=menu_category_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
    )


@store_router.get("/menu/{menu_item_id}")
@response_rapper()
@request_rapper()
def get_menu_detail(
    menu_item_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するメニュー詳細を取得する。

    Args:
        menu_item_id: 取得対象のメニュー商品ID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        商品、カテゴリー、画像URL、オプションを含む共通レスポンス。
    """
    return StoreController().get_menu_detail(
        store_id=auth_context.store_id,
        menu_item_id=menu_item_id,
    )


@store_router.put("/menu/{menu_item_id}")
@response_rapper()
@request_rapper()
def update_menu(
    request: MenuUpdateRequest,
    menu_item_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に属するメニュー基本情報を更新する。

    Args:
        request: 更新後の商品基本情報と任意の画像。
        menu_item_id: 更新対象のメニュー商品ID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        更新したメニュー商品IDを含む共通レスポンス。
    """
    return StoreController().update_menu(
        store_id=auth_context.store_id,
        menu_item_id=menu_item_id,
        request=request,
    )


@store_router.put("/menu/{menu_item_id}/option-groups")
@response_rapper()
@request_rapper()
def update_menu_option_groups(
    request: MenuOptionGroupsUpdateRequest,
    menu_item_id: int = Path(ge=1),
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証店舗に属する商品のオプション構成を完全同期する。

    Args:
        request: 更新後のオプショングループとオプションの全構成。
        menu_item_id: 更新対象のメニュー商品ID。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        更新後のオプショングループIDとオプションIDを含む共通レスポンス。
    """
    return StoreController().update_menu_option_groups(
        store_id=auth_context.store_id,
        menu_item_id=menu_item_id,
        request=request,
    )


@store_router.post("/menu", status_code=201)
@response_rapper()
@request_rapper()
def create_menu(
    request: MenuCreateRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗にメニューとオプションを登録する。

    Args:
        request: 商品、オプショングループ、オプションの登録情報。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        共通レスポンス形式で整形された登録済みデータのID。
    """
    return StoreController().create_menu(
        store_id=auth_context.store_id,
        request=request,
    )


@store_router.post("/wallet/nonce")
@response_rapper()
@request_rapper()
def create_wallet_nonce(
    request: WalletNonceCreateRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """ウォレット署名用 nonce を生成する。

    Args:
        request: nonce 発行に必要なリクエスト。
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        共通レスポンス形式で整形される nonce 発行結果。
    """
    return StoreController().create_wallet_nonce(
        store_id=auth_context.store_id,
        request=request,
    )


@store_router.post("/wallet")
@response_rapper()
@request_rapper()
def verify_and_create_wallet(
    request: WalletVerifyRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """ウォレット署名を検証し、ストアのウォレットを作成する。
    Args:
        request: ウォレットアドレス、署名、チェーン種別、ネットワーク名を含むリクエスト。
        auth_context: JWT認証で取得した店舗管理者情報。
    Returns:
        共通レスポンス形式で整形されたウォレット作成結果。
    """
    return StoreController().verify_and_create_wallet_nonce(
        store_id=auth_context.store_id,
        request=request,
    )


@store_router.delete("/wallet/{wallet_id}")
@response_rapper()
@request_rapper()
def delete_wallet(
    wallet_id: int,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """ウォレット署名を検証し、ストアのウォレットを作成する。
    Args:
        wallet_id: 削除対象のウォレット ID。
        auth_context: JWT認証で取得した店舗管理者情報。
    Returns:
        共通レスポンス形式で整形されたウォレット作成結果。
    """
    TeraidPayApiLog.info(
        f"ウォレットの削除を行います。 store_id={auth_context.store_id} wallet_id={wallet_id}")
    return StoreController().delete_wallet(
        store_id=auth_context.store_id,
        wallet_id=wallet_id,
    )
