"""メニューカテゴリーAPIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class MenuCategoryResponse(BaseModel):
    """メニューカテゴリー情報。"""

    menu_category_id: int = Field(..., description="Menu category ID")
    name: str = Field(..., description="Menu category name")
    image_url: str = Field(..., description="Presigned category image URL")
    display_order: int = Field(..., description="Display order")
    is_active: bool = Field(..., description="Active flag")


class MenuCategoryCreateResponse(BaseModel):
    """メニューカテゴリー登録 API のレスポンスモデル。"""

    menu_category_id: int = Field(..., description="Menu category ID")
    name: str = Field(..., description="Menu category name")
    display_order: int = Field(..., description="Display order")
    is_active: bool = Field(..., description="Active flag")


class MenuCategoryUpdateResponse(BaseModel):
    """メニューカテゴリー更新APIのレスポンスモデル。"""

    menu_category_id: int = Field(..., description="Menu category ID")
    name: str = Field(..., description="Menu category name")
    display_order: int = Field(..., description="Display order")
    is_active: bool = Field(..., description="Active flag")


class MenuCategoryPaginationResponse(BaseModel):
    """メニューカテゴリー一覧のページネーション情報。"""

    page: int = Field(..., description="Current page number")
    page_size: int | None = Field(
        ...,
        description="Number of categories per page; null when pagination is disabled",
    )
    total: int = Field(..., description="Total matching categories")
    total_pages: int = Field(..., description="Total number of pages")


class MenuCategoryListResponse(BaseModel):
    """メニューカテゴリー一覧 API のレスポンスモデル。"""

    menu_categories: list[MenuCategoryResponse] = Field(
        default_factory=list,
        description="Menu categories for the authenticated store",
    )
    pagination: MenuCategoryPaginationResponse
