"""端末初回有効化APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class DeviceActivateResponse(BaseModel):
    """初回有効化した端末のUUIDと認証情報を表す。

    Args:
        device_uuid: 事前登録時に割り当てられた端末UUID。
        device_credential: 成功時に一度だけ返す平文の端末認証情報。

    Returns:
        端末初回有効化APIのレスポンスモデル。
    """

    device_uuid: str = Field(description="端末UUID")
    device_credential: str = Field(repr=False, description="端末認証情報")
