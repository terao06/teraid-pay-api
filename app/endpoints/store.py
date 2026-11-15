from fastapi import APIRouter, Depends, Query
from app.controllers.store_controller import StoreController
from app.dependencies.store_manager_auth import (
    StoreManagerAuthContext,
    authenticate_store_manager,
)
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.requests.store_manager_login_request import StoreManagerLoginRequest
from app.models.requests.menu_category_create_request import MenuCategoryCreateRequest
from app.models.requests.menu_create_request import MenuCreateRequest
from app.core.utils.logging import TeraidPayApiLog

store_router = APIRouter()


@store_router.post("/manager/login")
@response_rapper()
@request_rapper()
def login_store_manager(request: StoreManagerLoginRequest):
    """店舗管理者をメールアドレスとパスワードで認証する。"""
    return StoreController().login_store_manager(request=request)


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
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗に紐づく有効なメニューカテゴリーを取得する。

    Args:
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        共通レスポンス形式で整形されるメニューカテゴリー一覧。
    """
    return StoreController().get_menu_categories(store_id=auth_context.store_id)


@store_router.post("/menu/categories", status_code=201)
@response_rapper()
@request_rapper()
def create_menu_category(
    request: MenuCategoryCreateRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """認証済み管理者の店舗へ画像付きメニューカテゴリーを登録する。"""
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
        auth_context: JWT認証で取得した店舗管理者情報。

    Returns:
        共通レスポンス形式で整形されるメニュー商品一覧。
    """
    return StoreController().get_menus(
        store_id=auth_context.store_id,
        name=name,
        menu_category_id=menu_category_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
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
