"""メニュー基本情報更新APIのリクエストモデルを提供する。"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.requests.menu_create_request import MenuImageExtension


class MenuUpdateRequest(BaseModel):
    """メニュー基本情報と任意の差し替え画像を表す。

    Args:
        menu_category_id: 更新後のカテゴリーID。未分類の場合はNone。
        name: 更新後の商品名。
        description: 更新後の商品説明。
        price: 更新後の基本価格。
        token_symbol: 更新後のトークンシンボル。
        menu_image: 任意のBase64形式の商品画像。
        image_extension: 任意の商品画像拡張子。
        is_available: 更新後の販売可能状態。
        display_order: 更新後の表示順。

    Returns:
        検証済みのメニュー基本情報更新リクエスト。
    """

    model_config = ConfigDict(extra="forbid")

    menu_category_id: int | None = Field(..., ge=1, description="Menu category ID")
    name: str = Field(..., min_length=1, max_length=255, description="Menu item name")
    description: str | None = Field(..., description="Menu item description")
    price: Decimal = Field(
        ...,
        ge=0,
        max_digits=20,
        decimal_places=6,
        description="Base price",
    )
    token_symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Token symbol",
    )
    menu_image: str | None = Field(
        default=None,
        description="Optional Base64-encoded menu image",
    )
    image_extension: MenuImageExtension | None = Field(
        default=None,
        description="Optional menu image extension",
    )
    is_available: bool = Field(..., description="Availability flag")
    display_order: int = Field(..., ge=0, description="Display order")

    @model_validator(mode="after")
    def validate_image_fields(self):
        """画像データと拡張子が同時に指定または省略されていることを検証する。

        Args:
            なし。

        Returns:
            検証済みのリクエストモデル。

        Raises:
            ValueError: 画像データと拡張子の一方だけが指定された場合。
        """
        if (self.menu_image is None) != (self.image_extension is None):
            raise ValueError(
                "menu_image and image_extension must be specified together"
            )
        return self
