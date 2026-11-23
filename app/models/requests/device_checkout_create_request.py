"""まとめ払いと別会計の作成リクエストを検証する。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.utils.device_request import SIGNED_BIGINT_MAX


class DeviceAllUnpaidCheckoutRequest(BaseModel):
    """来店セッションの未払い明細すべてを会計対象にする。

    Args:
        scope: 未払い全件を指定する固定値 `all_unpaid`。

    Returns:
        検証済みのまとめ払いリクエスト。

    Raises:
        ValidationError: 対象範囲が異なるか、余分な項目が指定された場合。
    """

    model_config = ConfigDict(extra="forbid")

    scope: Literal["all_unpaid"]


class DeviceCheckoutItemRequest(BaseModel):
    """別会計で支払う注文明細と数量を表す。

    Args:
        menu_order_item_id: プラスの符号付きBIGINTの範囲にある注文明細ID。
        quantity: 今回支払う数量。プラスの符号なしINTの範囲で指定する。

    Returns:
        検証済みの会計対象明細。

    Raises:
        ValidationError: ID、数量、または項目の構成が不正な場合。
    """

    model_config = ConfigDict(extra="forbid")

    menu_order_item_id: Annotated[int, Field(strict=True, ge=1, le=SIGNED_BIGINT_MAX)]
    quantity: Annotated[int, Field(strict=True, ge=1, le=4_294_967_295)]


class DeviceSelectedItemsCheckoutRequest(BaseModel):
    """来店セッション内の指定した明細と数量を会計対象にする。

    Args:
        scope: 別会計を指定する固定値 `selected_items`。
        items: 会計対象の注文明細と数量の空でない一覧。

    Returns:
        検証済みの別会計リクエスト。

    Raises:
        ValidationError: 対象範囲や明細の指定が不正な場合。
    """

    model_config = ConfigDict(extra="forbid")

    scope: Literal["selected_items"]
    items: Annotated[list[DeviceCheckoutItemRequest], Field(min_length=1)]

    @field_validator("items")
    @classmethod
    def validate_unique_items(cls, items: list[DeviceCheckoutItemRequest]) -> list[DeviceCheckoutItemRequest]:
        """各注文明細IDが一度だけ指定されていることを確認する。

        Args:
            items: 検証する会計対象明細。

        Returns:
            重複のない会計対象明細。

        Raises:
            ValueError: 同じ注文明細IDが複数回指定された場合。
        """
        if len({item.menu_order_item_id for item in items}) != len(items):
            raise ValueError("注文明細IDは一度だけ指定してください。")
        return items


DeviceCheckoutCreateRequest = DeviceAllUnpaidCheckoutRequest | DeviceSelectedItemsCheckoutRequest
