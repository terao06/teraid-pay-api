from fastapi import APIRouter
from app.controllers.user_controller import UserController
from app.core.utils.logging import TeraidPayApiLog
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.wallet_permit_update_request import WalletPermitUpdateRequest
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


@user_router.get("/{user_id}/wallet/permit")
@response_rapper()
@request_rapper()
def get_user_wallet_permit(user_id: int):
    """ユーザーウォレットの JPYC permit 署名に必要な情報を取得する。"""
    return UserController().get_user_wallet_permit(user_id=user_id)


@user_router.post("/{user_id}/wallet/{wallet_id}/permit")
@response_rapper()
@request_rapper()
def update_wallet_permit_state(user_id: int, wallet_id: int, request: WalletPermitUpdateRequest):
    """ユーザーウォレットの permit 許可状態を更新する。"""
    TeraidPayApiLog.info(
        f"ウォレットの permit 許可状態更新を行います。 "
        f"user_id={user_id} "
        f"wallet_id={wallet_id} "
        f"allowance_value={request.allowance_value} "
        f"signature_deadline={request.signature_deadline} "
        f"signature_recovery_id={request.signature_recovery_id} "
        f"signature_first_32_bytes={request.signature_first_32_bytes} "
        f"signature_second_32_bytes={request.signature_second_32_bytes}")

    return UserController().update_wallet_permit_state(
        wallet_id=wallet_id,
        value=request.allowance_value,
        deadline=request.signature_deadline,
        signature_recovery_id=request.signature_recovery_id,
        signature_first_32_bytes=request.signature_first_32_bytes,
        signature_second_32_bytes=request.signature_second_32_bytes,
    )


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
