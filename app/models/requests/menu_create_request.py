from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class MenuImageExtension(Enum):
    """メニュー画像として登録可能な拡張子。"""

    JPEG = "jpeg"
    PNG = "png"
    JPG = "jpg"


class MenuOptionCreateRequest(BaseModel):
    """メニューオプション登録情報。"""

    name: str = Field(..., max_length=100, description="Menu option name")
    additional_price: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=20,
        decimal_places=6,
        description="Additional price",
    )
    display_order: int = Field(default=0, ge=0, description="Display order")
    is_available: bool = Field(default=True, description="Availability flag")


class MenuOptionGroupCreateRequest(BaseModel):
    """メニューオプショングループ登録情報。"""

    name: str = Field(..., max_length=100, description="Menu option group name")
    min_selections: int = Field(default=0, ge=0, description="Minimum selections")
    max_selections: int = Field(default=1, gt=0, description="Maximum selections")
    display_order: int = Field(default=0, ge=0, description="Display order")
    is_active: bool = Field(default=True, description="Active flag")
    options: list[MenuOptionCreateRequest] = Field(
        ...,
        description="Menu options",
    )

    @model_validator(mode="after")
    def validate_selection_range(self):
        """最小選択数が最大選択数以下であることを検証する。"""
        if self.min_selections > self.max_selections:
            raise ValueError("min_selections must be less than or equal to max_selections")
        return self


class MenuCreateRequest(BaseModel):
    """メニュー登録 API のリクエストモデル。"""

    menu_category_id: int | None = Field(
        default=None,
        ge=1,
        description="Menu category ID",
    )
    name: str = Field(..., max_length=255, description="Menu item name")
    description: str | None = Field(default=None, description="Menu item description")
    price: Decimal = Field(
        ...,
        ge=0,
        max_digits=20,
        decimal_places=6,
        description="Base price",
    )
    token_symbol: str = Field(default="JPYC", max_length=20, description="Token symbol")
    menu_image: str = Field(..., description="Base64-encoded menu image")
    image_extension: MenuImageExtension = Field(..., description="Menu image extension")
    is_available: bool = Field(default=True, description="Availability flag")
    display_order: int = Field(default=0, ge=0, description="Display order")
    option_groups: list[MenuOptionGroupCreateRequest] = Field(
        ...,
        description="Menu option groups",
    )
