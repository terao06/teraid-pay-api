"""端末用カテゴリー別メニューのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class DeviceMenuOptionResponse(BaseModel):
    """注文端末で選択できるオプションを表す。

    Args:
        menu_option_id: オプションID。
        name: オプション名。
        additional_price: 小数点以下6桁で表した追加料金。
        display_order: 表示順。

    Returns:
        オプションの表示情報。
    """

    menu_option_id: int
    name: str
    additional_price: str = Field(description="小数点以下6桁で表した追加料金。")
    display_order: int


class DeviceMenuOptionGroupResponse(BaseModel):
    """注文端末向けのオプショングループと選択ルールを表す。

    Args:
        menu_option_group_id: オプショングループID。
        name: グループ名。
        min_selections: 最小選択数。
        max_selections: 最大選択数。
        display_order: 表示順。
        options: 選択可能なオプションの一覧。

    Returns:
        選択ルールを含むグループの表示情報。
    """

    menu_option_group_id: int
    name: str
    min_selections: int
    max_selections: int
    display_order: int
    options: list[DeviceMenuOptionResponse]


class DeviceMenuItemResponse(BaseModel):
    """注文端末に表示する販売可能な商品を表す。

    Args:
        menu_item_id: 商品ID。
        name: 商品名。
        price: 小数点以下6桁で表した基本価格。
        token_symbol: 価格のトークンシンボル。
        image_url: 商品画像の署名付きGET URL。
        display_order: 表示順。
        option_groups: 商品の有効なオプショングループ一覧。

    Returns:
        画像と選択ルールを含む商品の表示情報。
    """

    menu_item_id: int
    name: str
    price: str = Field(description="小数点以下6桁で表した基本価格。")
    token_symbol: str
    image_url: str = Field(description="商品画像の署名付きGET URL。")
    display_order: int
    option_groups: list[DeviceMenuOptionGroupResponse]


class DeviceMenuItemListResponse(BaseModel):
    """注文端末で選択したカテゴリーの商品一覧を表す。

    Args:
        menu_items: 販売可能な商品の表示順の一覧。該当商品がなければ空配列。

    Returns:
        カテゴリー別メニュー取得APIの成功レスポンス。
    """

    menu_items: list[DeviceMenuItemResponse]
