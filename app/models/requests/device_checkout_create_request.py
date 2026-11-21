"""会計作成で指定できる対象範囲と注文IDを検証する。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.utils.device_request import SIGNED_BIGINT_MAX


class AllUnpaidCheckoutRequest(BaseModel):
    """来店セッションの未払い注文をすべて会計対象にする。

    Args:
        scope: 一括会計を指定する値。

    Returns:
        対象の注文IDを持たない一括会計リクエスト。

    Raises:
        ValidationError: 対象範囲が違うか、余分な項目が指定された場合。
    """

    model_config = ConfigDict(extra="forbid")

    scope: Literal["all_unpaid"]


class SingleOrderCheckoutRequest(BaseModel):
    """指定した未払い注文1件を会計対象にする。

    Args:
        scope: 注文ごとの会計を指定する値。
        menu_order_id: 会計対象の注文ID。

    Returns:
        対象の注文IDを含む会計リクエスト。

    Raises:
        ValidationError: 注文IDが未指定または不正、もしくは余分な項目がある場合。
    """

    model_config = ConfigDict(extra="forbid")

    scope: Literal["single_order"]
    menu_order_id: Annotated[int, Field(strict=True, ge=1, le=SIGNED_BIGINT_MAX)]


DeviceCheckoutCreateRequest = AllUnpaidCheckoutRequest | SingleOrderCheckoutRequest
