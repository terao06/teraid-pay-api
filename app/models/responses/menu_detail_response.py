"""メニュー詳細取得APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field

from app.models.responses.menu_list_response import MenuItemResponse


class MenuOptionResponse(BaseModel):
    """メニュー詳細に含めるオプション情報を表す。

    Args:
        menu_option_id: オプションID。
        name: オプション名。
        additional_price: 小数点以下6桁の追加料金文字列。
        display_order: 表示順。
        is_available: 選択可能状態。

    Returns:
        メニューオプションのレスポンスモデル。
    """

    menu_option_id: int = Field(..., description="Menu option ID")
    name: str = Field(..., description="Menu option name")
    additional_price: str = Field(..., description="Additional price")
    display_order: int = Field(..., description="Display order")
    is_available: bool = Field(..., description="Availability flag")


class MenuOptionGroupResponse(BaseModel):
    """メニュー詳細に含めるオプショングループ情報を表す。

    Args:
        menu_option_group_id: オプショングループID。
        name: オプショングループ名。
        min_selections: 最小選択数。
        max_selections: 最大選択数。
        display_order: 表示順。
        is_active: 有効状態。
        options: グループに属するオプション一覧。

    Returns:
        オプショングループのレスポンスモデル。
    """

    menu_option_group_id: int = Field(..., description="Menu option group ID")
    name: str = Field(..., description="Menu option group name")
    min_selections: int = Field(..., description="Minimum selections")
    max_selections: int = Field(..., description="Maximum selections")
    display_order: int = Field(..., description="Display order")
    is_active: bool = Field(..., description="Active flag")
    options: list[MenuOptionResponse] = Field(
        default_factory=list,
        description="Menu options",
    )


class MenuDetailResponse(MenuItemResponse):
    """カテゴリーとオプションを含むメニュー商品詳細を表す。

    Args:
        option_groups: 商品に属するオプショングループ一覧。
        **data: 商品、カテゴリー、画像URLを含むメニュー基本情報。

    Returns:
        メニュー詳細のレスポンスモデル。
    """

    option_groups: list[MenuOptionGroupResponse] = Field(
        default_factory=list,
        description="Menu option groups",
    )
