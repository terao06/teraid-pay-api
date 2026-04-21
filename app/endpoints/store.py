from fastapi import APIRouter
from app.controllers.store_controller import StoreController
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import StoreWalletVerifyRequest
from app.core.utils.logging import TeraidPayApiLog

store_router = APIRouter()


@store_router.get("/{store_id}/wallet")
@response_rapper()
@request_rapper()
def store_root(store_id: int):
    """店舗のウォレット一覧を取得する。

    Args:
        store_id: 対象店舗の ID。

    Returns:
        共通レスポンス形式で整形されるウォレット一覧。
    """
    return StoreController().get_store_wallet(store_id=store_id)


@store_router.post("/{store_id}/wallet/nonce")
@response_rapper()
@request_rapper()
def create_wallet_nonce(store_id: int, request: WalletNonceCreateRequest):
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
def verify_and_create_wallet(store_id: int, request: StoreWalletVerifyRequest):
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
def delete_wallet(store_id: int, wallet_id: int):
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
