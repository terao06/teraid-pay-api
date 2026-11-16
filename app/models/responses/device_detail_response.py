"""デバイス詳細情報取得APIのレスポンスモデルを提供する。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceDetailResponse(BaseModel):
    """管理画面へ表示可能なデバイス詳細情報を表す。

    Args:
        device_id: デバイスID。
        device_name: デバイス名。
        is_active: 利用可能フラグ。
        activated_at: 初回有効化日時。
        last_authenticated_at: 最終認証日時。
        created_at: 登録日時。
        updated_at: 更新日時。

    Returns:
        デバイス詳細情報取得APIのレスポンスモデル。
    """

    device_id: int = Field(..., description="Device ID")
    device_name: str = Field(..., description="デバイス名")
    is_active: bool = Field(..., description="利用可能フラグ")
    activated_at: datetime | None = Field(None, description="初回有効化日時")
    last_authenticated_at: datetime | None = Field(None, description="最終認証日時")
    created_at: datetime = Field(..., description="登録日時")
    updated_at: datetime = Field(..., description="更新日時")
