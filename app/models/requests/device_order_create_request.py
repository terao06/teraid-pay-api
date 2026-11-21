"""端末から送られた注文内容を検証するリクエストモデルを提供する。"""

from functools import partial
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.core.utils.device_request import SIGNED_BIGINT_MAX, validate_decimal_id


_MenuId = Annotated[int, Field(strict=True, ge=1, le=SIGNED_BIGINT_MAX)]
_Quantity = Annotated[int, Field(strict=True, ge=1, le=4_294_967_295)]


class DeviceOrderPathRequest(BaseModel):
    """注文と会計のAPIで使う来店セッションIDを検証する。

    Args:
        visit_session_id: パスで指定された来店セッションID。

    Returns:
        検証済みのパス入力。

    Raises:
        ValidationError: 来店セッションIDの形式や範囲が不正な場合。
    """

    visit_session_id: Annotated[
        int,
        Field(ge=1, le=SIGNED_BIGINT_MAX),
        BeforeValidator(partial(validate_decimal_id, label="来店セッションID")),
    ]


class DeviceOrderOptionRequest(BaseModel):
    """商品1個に対するオプションの指定を検証する。

    Args:
        menu_option_id: 選択するオプションのID。
        option_quantity: 商品1個当たりのオプション数量。

    Returns:
        検証済みのオプション指定。

    Raises:
        ValidationError: IDまたは数量の形式や範囲が不正な場合。
    """

    menu_option_id: _MenuId
    option_quantity: _Quantity


class DeviceOrderItemRequest(BaseModel):
    """注文の商品明細を検証する。

    Args:
        menu_item_id: 注文する商品のID。
        quantity: 商品の数量。
        options: 選択したオプション。選択しない場合は空配列。

    Returns:
        検証済みの商品明細。

    Raises:
        ValidationError: ID、数量、またはオプションの指定が不正な場合。
    """

    menu_item_id: _MenuId
    quantity: _Quantity
    options: list[DeviceOrderOptionRequest]


class DeviceOrderCreateRequest(BaseModel):
    """一度の注文に含まれる商品明細を検証する。

    Args:
        items: 1件以上の商品明細。

    Returns:
        検証済みの注文登録リクエスト。

    Raises:
        ValidationError: 明細が空、または不正な場合。
    """

    items: list[DeviceOrderItemRequest] = Field(min_length=1)
