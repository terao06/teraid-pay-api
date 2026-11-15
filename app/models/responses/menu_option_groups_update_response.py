"""メニューオプション構成更新APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class MenuOptionGroupUpdateResult(BaseModel):
    """更新後のオプショングループと配下オプションのIDを表す。

    Args:
        menu_option_group_id: オプショングループID。
        menu_option_ids: グループに属する更新後のオプションID一覧。

    Returns:
        更新済みオプショングループのID情報。
    """

    menu_option_group_id: int = Field(..., description="Menu option group ID")
    menu_option_ids: list[int] = Field(..., description="Menu option IDs")


class MenuOptionGroupsUpdateResponse(BaseModel):
    """更新した商品のオプション構成IDを表す。

    Args:
        menu_item_id: メニュー商品ID。
        menu_option_groups: 更新後のグループとオプションのID一覧。

    Returns:
        更新後のメニューオプション構成。
    """

    menu_item_id: int = Field(..., description="Menu item ID")
    menu_option_groups: list[MenuOptionGroupUpdateResult] = Field(...)
