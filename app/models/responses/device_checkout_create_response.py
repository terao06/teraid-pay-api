"""作成した会計と保存済みの注文明細を返す。"""

from pydantic import BaseModel

from app.models.responses.device_order_history_response import DeviceOrderHistoryItemResponse


class DeviceCheckoutOrderResponse(BaseModel):
    """会計に含まれる注文1件の明細を表す。

    Args:
        menu_order_id: 会計対象の注文ID。
        total_amount: 注文合計を表す小数点以下6桁の文字列。
        items: 注文時に保存された商品とオプションの明細。

    Returns:
        保存済みの注文金額と商品明細。
    """

    menu_order_id: int
    total_amount: str
    items: list[DeviceOrderHistoryItemResponse]


class DeviceCheckoutCreateResponse(BaseModel):
    """確認待ちの会計IDと支払い対象の内容を表す。

    Args:
        checkout_id: 作成した会計のID。
        orders: 会計対象の注文と明細。
        total_amount: 支払い対象の合計を表す小数点以下6桁の文字列。
        token_symbol: 対象注文で共通するトークンシンボル。

    Returns:
        端末が会計内容の確認に使うレスポンス。
    """

    checkout_id: int
    orders: list[DeviceCheckoutOrderResponse]
    total_amount: str
    token_symbol: str
