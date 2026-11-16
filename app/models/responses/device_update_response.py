"""デバイス更新APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class DeviceUpdateResponse(BaseModel):
    """更新したデバイスIDを表す。

    Args:
        device_id: 更新したデバイスID。

    Returns:
        デバイス更新APIのレスポンスモデル。
    """

    device_id: int = Field(..., description="Device ID")
