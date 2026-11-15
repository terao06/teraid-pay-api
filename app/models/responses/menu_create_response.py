from pydantic import BaseModel, Field


class MenuCreateResponse(BaseModel):
    """登録したメニュー商品IDを返すレスポンスモデル。"""

    menu_item_id: int = Field(..., description="Menu item ID")
