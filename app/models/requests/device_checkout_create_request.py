"""一括会計の作成リクエストを検証する。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DeviceCheckoutCreateRequest(BaseModel):
    """来店セッションの未払い注文をすべて会計対象にする。

    Args:
        scope: 既存端末が送信する固定値 `all_unpaid`。

    Returns:
        一括会計の作成リクエスト。

    Raises:
        ValidationError: 固定値と異なるか、余分な項目が指定された場合。
    """

    model_config = ConfigDict(extra="forbid")

    scope: Literal["all_unpaid"]
