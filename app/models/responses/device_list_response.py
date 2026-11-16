"""デバイス一覧取得APIのレスポンスモデルを提供する。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceListItemResponse(BaseModel):
    """デバイス一覧の1件分を表す。

    Args:
        device_id: デバイスID。
        device_name: デバイス名。
        is_active: 利用可能フラグ。
        created_at: 登録日時。

    Returns:
        デバイス一覧の明細モデル。
    """

    device_id: int = Field(..., description="Device ID")
    device_name: str = Field(..., description="デバイス名")
    is_active: bool = Field(..., description="利用可能フラグ")
    created_at: datetime = Field(..., description="登録日時")


class DevicePaginationResponse(BaseModel):
    """デバイス一覧のページネーション情報を表す。

    Args:
        page: 現在のページ番号。
        page_size: 1ページの件数。
        total: 該当するデバイスの総件数。
        total_pages: 総ページ数。

    Returns:
        デバイス一覧のページネーションモデル。
    """

    page: int = Field(..., description="現在のページ番号")
    page_size: int = Field(..., description="1ページの件数")
    total: int = Field(..., description="該当するデバイスの総件数")
    total_pages: int = Field(..., description="総ページ数")


class DeviceListResponse(BaseModel):
    """デバイス一覧とページネーション情報を表す。

    Args:
        devices: デバイス一覧。
        pagination: ページネーション情報。

    Returns:
        デバイス一覧取得APIのレスポンスモデル。
    """

    devices: list[DeviceListItemResponse] = Field(
        default_factory=list,
        description="デバイス一覧",
    )
    pagination: DevicePaginationResponse
