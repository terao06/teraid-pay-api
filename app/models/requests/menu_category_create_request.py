from enum import Enum

from pydantic import BaseModel, Field


class MenuCategoryImageExtension(Enum):
    """カテゴリー画像として登録可能な拡張子。"""

    JPEG = "jpeg"
    PNG = "png"
    JPG = "jpg"


class MenuCategoryCreateRequest(BaseModel):
    """メニューカテゴリー登録 API のリクエストモデル。"""

    name: str = Field(..., min_length=1, max_length=100, description="Menu category name")
    category_image: str = Field(..., description="Base64-encoded category image")
    image_extension: MenuCategoryImageExtension = Field(
        ...,
        description="Category image extension",
    )
    display_order: int = Field(default=0, ge=0, description="Display order")
    is_active: bool = Field(default=True, description="Active flag")
