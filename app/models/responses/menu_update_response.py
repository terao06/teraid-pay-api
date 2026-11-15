"""メニュー基本情報更新APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class MenuUpdateResponse(BaseModel):
    """更新したメニュー商品IDを表す。

    Args:
        menu_item_id: メニュー商品ID。

    Returns:
        更新したメニュー商品IDのレスポンス。
    """

    menu_item_id: int = Field(..., description="Menu item ID")
