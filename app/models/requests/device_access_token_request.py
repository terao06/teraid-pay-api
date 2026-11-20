"""端末アクセストークン発行APIのリクエストモデルを提供する。"""

from uuid import UUID

from pydantic import BaseModel, Field


class DeviceAccessTokenRequest(BaseModel):
    """端末UUIDと認証情報を検証する。

    Args:
        device_uuid: 初回有効化時に受け取った端末UUID。
        device_credential: 初回有効化時に受け取った平文の端末認証情報。

    Returns:
        検証済みの端末認証リクエスト。

    Raises:
        ValidationError: 端末UUIDまたは認証情報が未指定、または形式不正の場合。
    """

    device_uuid: UUID = Field(description="端末UUID")
    device_credential: str = Field(
        strict=True,
        min_length=1,
        repr=False,
        description="端末認証情報",
    )
