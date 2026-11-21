"""端末用の注文登録レスポンスを提供する。"""

from pydantic import BaseModel


class DeviceOrderCreateResponse(BaseModel):
    """保存された注文のIDと金額を返す。

    Args:
        menu_order_id: 注文ID。
        total_amount: 小数点以下6桁の合計金額。
        token_symbol: 注文に使用するトークンのシンボル。

    Returns:
        新規登録または再送時の注文登録レスポンス。
    """

    menu_order_id: int
    total_amount: str
    token_symbol: str
