"""端末用注文履歴のレスポンスモデルを提供する。"""

from datetime import datetime

from pydantic import BaseModel

from app.models.mysql.menu_order import OrderStatus


class DeviceOrderHistoryOptionResponse(BaseModel):
    """注文時点のオプション明細を表す。

    Args:
        option_group_name: 注文時のグループ名。
        option_name: 注文時のオプション名。
        additional_price: オプション1個の追加単価を表す小数文字列。
        option_quantity: 商品1個当たりのオプション数量。

    Returns:
        注文時の名称と追加単価を保持するオプション明細。
    """

    option_group_name: str
    option_name: str
    additional_price: str
    option_quantity: int


class DeviceOrderHistoryItemResponse(BaseModel):
    """注文時点の商品明細を表す。

    Args:
        menu_item_name: 注文時の商品名。
        unit_price: 注文時の基本単価を表す小数文字列。
        quantity: 商品の注文数量。
        line_amount: オプションを含む商品明細の金額を表す小数文字列。
        options: 商品1個当たりのオプション明細。

    Returns:
        保存済みの商品とオプションの明細。
    """

    menu_item_name: str
    unit_price: str
    quantity: int
    line_amount: str
    options: list[DeviceOrderHistoryOptionResponse]


class DeviceOrderHistoryEntryResponse(BaseModel):
    """注文履歴の1件を表す。

    Args:
        menu_order_id: 注文ID。
        created_at: UTCの注文受付日時。
        status: 取得時点の注文状態。
        total_amount: 注文合計を表す小数文字列。
        token_symbol: 注文に使用するトークンのシンボル。
        items: 保存済みの商品明細。

    Returns:
        注文の現在の状態と保存済み明細を含む履歴。
    """

    menu_order_id: int
    created_at: datetime
    status: OrderStatus
    total_amount: str
    token_symbol: str
    items: list[DeviceOrderHistoryItemResponse]


class DeviceOrderHistoryResponse(BaseModel):
    """来店セッションの注文履歴を返す。

    Args:
        orders: 注文受付日時の降順に並ぶ注文一覧。

    Returns:
        注文履歴レスポンス。注文がない場合の一覧は空。
    """

    orders: list[DeviceOrderHistoryEntryResponse]
