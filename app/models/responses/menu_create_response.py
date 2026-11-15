from pydantic import BaseModel, Field


class MenuOptionGroupCreateResponse(BaseModel):
    """登録したオプショングループとオプションのID。"""

    menu_option_group_id: int = Field(..., description="Menu option group ID")
    menu_option_ids: list[int] = Field(
        default_factory=list,
        description="Menu option IDs",
    )


class MenuCreateResponse(BaseModel):
    """メニュー登録 API のレスポンスモデル。"""

    menu_item_id: int = Field(..., description="Menu item ID")
    menu_option_groups: list[MenuOptionGroupCreateResponse] = Field(
        default_factory=list,
        description="Created menu option groups",
    )
