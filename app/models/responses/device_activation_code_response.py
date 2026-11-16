"""デバイス有効化コード発行APIのレスポンスモデルを提供する。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceActivationCodeResponse(BaseModel):
    """発行したデバイス有効化コードと有効期限を表す。

    Args:
        device_id: 対象のデバイスID。
        activation_code: 管理画面へ一度だけ返す平文の有効化コード。
        qr_code_image: 有効化情報を格納したBase64形式のPNG画像。
        activation_expires_at: 有効化コードの有効期限。

    Returns:
        デバイス有効化コード発行APIのレスポンスモデル。
    """

    device_id: int = Field(..., description="Device ID")
    activation_code: str = Field(..., description="Activation code")
    qr_code_image: str = Field(..., description="Base64-encoded QR code PNG data URL")
    activation_expires_at: datetime = Field(
        ...,
        description="Activation code expiration date and time",
    )
