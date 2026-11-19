"""デバイス削除結果のレスポンスモデルを提供する。"""

from pydantic import BaseModel


class DeviceDeleteResponse(BaseModel):
    """論理削除したデバイスのIDを返す。

    Args:
        device_id: 論理削除したデバイスID。

    Returns:
        削除したデバイスIDを保持するレスポンス。
    """

    device_id: int
