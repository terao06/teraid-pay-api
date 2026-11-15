from pydantic import BaseModel, Field


class MenuCategoryResponse(BaseModel):
    """メニューカテゴリー情報。"""

    menu_category_id: int = Field(..., description="Menu category ID")
    name: str = Field(..., description="Menu category name")
    display_order: int = Field(..., description="Display order")


class MenuCategoryListResponse(BaseModel):
    """メニューカテゴリー一覧 API のレスポンスモデル。"""

    menu_categories: list[MenuCategoryResponse] = Field(
        default_factory=list,
        description="Active menu categories for the authenticated store",
    )
