from fastapi import APIRouter, Depends
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
from app.core.utils.logging import TeraidPayApiLog

store_router = APIRouter()


@store_router.post("/manager/login")
@response_rapper()
@request_rapper()
def login_store_manager(request: StoreManagerLoginRequest):
    """店舗管理者をメールアドレスとパスワードで認証する。"""
    return StoreController().login_store_manager(request=request)


@store_router.get("/{store_id}/wallet")
@response_rapper()
@request_rapper()
def get_wallet_nonce(
    store_id: int,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """店舗のウォレット情報を取得する。

    Args:
        store_id: 対象店舗の ID。

    Returns:
        共通レスポンス形式で整形されるウォレット情報。
    """
    return StoreController().get_store_wallet(store_id=store_id)


@store_router.post("/{store_id}/wallet/nonce")
@response_rapper()
@request_rapper()
def create_wallet_nonce(
    store_id: int,
    request: WalletNonceCreateRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """ウォレット署名用 nonce を生成する。

    Args:
        store_id: 対象店舗の ID。
        request: nonce 発行に必要なリクエスト。

    Returns:
        共通レスポンス形式で整形される nonce 発行結果。
    """
    return StoreController().create_wallet_nonce(
        store_id=store_id,
        request=request,
    )


@store_router.post("/{store_id}/wallet")
@response_rapper()
@request_rapper()
def verify_and_create_wallet(
    store_id: int,
    request: WalletVerifyRequest,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """ウォレット署名を検証し、ストアのウォレットを作成する。
    Args:
        store_id: 対象ストアの ID。
        request: ウォレットアドレス、署名、チェーン種別、ネットワーク名を含むリクエスト。
    Returns:
        共通レスポンス形式で整形されたウォレット作成結果。
    """
    return StoreController().verify_and_create_wallet_nonce(
        store_id=store_id,
        request=request,
    )


@store_router.delete("/{store_id}/wallet/{wallet_id}")
@response_rapper()
@request_rapper()
def delete_wallet(
    store_id: int,
    wallet_id: int,
    auth_context: StoreManagerAuthContext = Depends(authenticate_store_manager),
):
    """ウォレット署名を検証し、ストアのウォレットを作成する。
    Args:
        wallet_id: 対象ストアの ID。
    Returns:
        共通レスポンス形式で整形されたウォレット作成結果。
    """
    TeraidPayApiLog.info(
        f"ウォレットの削除を行います。 store_id={store_id} wallet_id={wallet_id}")
    return StoreController().delete_wallet(
        wallet_id=wallet_id,
    )
