"""デバイス登録APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class DeviceCreateResponse(BaseModel):
    """登録したデバイスIDを表す。

    Args:
        device_id: 登録したデバイスID。

    Returns:
        デバイス登録APIのレスポンスモデル。
    """

    device_id: int = Field(..., description="Device ID")
