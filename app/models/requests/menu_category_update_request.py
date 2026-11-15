"""メニューカテゴリー更新APIのリクエストモデルを提供する。"""

from pydantic import BaseModel, Field, model_validator

from app.models.requests.menu_category_create_request import (
    MenuCategoryImageExtension,
)


class MenuCategoryUpdateRequest(BaseModel):
    """メニューカテゴリー更新APIの入力値を表す。"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Menu category name",
    )
    category_image: str | None = Field(
        default=None,
        description="Optional Base64-encoded category image",
    )
    image_extension: MenuCategoryImageExtension | None = Field(
        default=None,
        description="Optional category image extension",
    )
    display_order: int = Field(..., ge=0, description="Display order")
    is_active: bool = Field(..., description="Active flag")

    @model_validator(mode="after")
    def validate_image_fields(self):
        """画像データと拡張子が同時に指定または省略されていることを検証する。

        Returns:
            検証済みのリクエストモデル。

        Raises:
            ValueError: 画像データと拡張子の一方だけが指定された場合。
        """
        if (self.category_image is None) != (self.image_extension is None):
            raise ValueError(
                "category_image and image_extension must be specified together"
            )
        return self
