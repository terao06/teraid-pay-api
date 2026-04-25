from fastapi import APIRouter
from app.controllers.user_controller import UserController
from app.core.utils.logging import TeraidPayApiLog
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest

user_router = APIRouter()


@user_router.get("/{user_id}/wallet")
@response_rapper()
@request_rapper()
def get_user_wallet(user_id: int):
    """ユーザーのウォレット情報を取得する。

    Args:
        user_id: 対象店舗の ID。

    Returns:
        共通レスポンス形式で整形されるウォレット一覧。
    """
    return UserController().get_user_wallet(user_id=user_id)


@user_router.post("/{user_id}/wallet/nonce")
@response_rapper()
@request_rapper()
def create_wallet_nonce(user_id: int, request: WalletNonceCreateRequest):
    """ウォレット署名用 nonce を生成する。

    Args:
        user_id: 対象ユーザーの ID。
        request: nonce 発行に必要なリクエスト。

    Returns:
        共通レスポンス形式で整形される nonce 発行結果。
    """
    return UserController().create_wallet_nonce(
        user_id=user_id,
        request=request,
    )


@user_router.post("/{user_id}/wallet")
@response_rapper()
@request_rapper()
def verify_and_create_wallet(user_id: int, request: WalletVerifyRequest):
    """ウォレット署名を検証し、ストアのウォレットを作成する。
    Args:
        user_id: 対象ストアの ID。
        request: ウォレットアドレス、署名、チェーン種別、ネットワーク名を含むリクエスト。
    Returns:
        共通レスポンス形式で整形されたウォレット作成結果。
    """
    return UserController().verify_and_create_wallet_nonce(
        user_id=user_id,
        request=request,
    )


@user_router.delete("/{user_id}/wallet/{wallet_id}")
@response_rapper()
@request_rapper()
def delete_wallet(user_id: int, wallet_id: int):
    """ウォレット署名を検証し、ストアのウォレットを作成する。
    Args:
        wallet_id: 対象ストアの ID。
    Returns:
        共通レスポンス形式で整形されたウォレット作成結果。
    """
    TeraidPayApiLog.info(
        f"ウォレットの削除を行います。 user_id={user_id} wallet_id={wallet_id}")
    return UserController().delete_wallet(
        wallet_id=wallet_id,
    )
