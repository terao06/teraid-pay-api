"""作成した会計と保存済みの注文明細を返す。"""

from pydantic import BaseModel

from app.models.responses.device_order_history_response import DeviceOrderHistoryItemResponse


class DeviceCheckoutItemResponse(DeviceOrderHistoryItemResponse):
    """会計対象の注文明細ID、数量、金額と注文時の商品情報を表す。

    Args:
        menu_order_item_id: 注文時に採番した明細ID。
        menu_item_name: 注文時の商品名。
        unit_price: 注文時の基本単価を表す小数文字列。
        quantity: この会計で支払う数量。
        line_amount: オプションを含む対象数量分の金額を表す小数文字列。
        options: 商品1個当たりのオプション明細。

    Returns:
        端末が会計内容を確認するための商品明細。
    """

    menu_order_item_id: int


class DeviceCheckoutOrderResponse(BaseModel):
    """会計に含まれる注文1件の明細を表す。

    Args:
        menu_order_id: 会計対象の注文ID。
        total_amount: この注文の会計対象額を表す小数点以下6桁の文字列。
        items: この会計に含まれる商品とオプションの明細。

    Returns:
        注文単位にまとめた会計対象額と明細。
    """

    menu_order_id: int
    total_amount: str
    items: list[DeviceCheckoutItemResponse]


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
