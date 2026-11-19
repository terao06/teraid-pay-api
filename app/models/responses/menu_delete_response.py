"""メニュー削除APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class MenuDeleteResponse(BaseModel):
    """削除したメニュー商品IDを表す。

    Args:
        menu_item_id: 削除したメニュー商品ID。

    Returns:
        削除結果を表すレスポンス。
    """

    menu_item_id: int = Field(..., description="削除したメニュー商品ID")
