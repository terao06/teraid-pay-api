from pydantic import BaseModel, Field


class MenuItemResponse(BaseModel):
    """メニュー商品情報。"""

    menu_item_id: int = Field(..., description="Menu item ID")
    menu_category_id: int | None = Field(
        default=None,
        description="Menu category ID",
    )
    menu_category_name: str | None = Field(
        default=None,
        description="Menu category name",
    )
    name: str = Field(..., description="Menu item name")
    description: str | None = Field(default=None, description="Menu item description")
    price: str = Field(..., description="Menu item price")
    token_symbol: str = Field(..., description="Token symbol")
    image_url: str = Field(..., description="Presigned menu image URL")
    is_available: bool = Field(..., description="Availability flag")
    display_order: int = Field(..., description="Display order")


class MenuPaginationResponse(BaseModel):
    """メニュー一覧のページング情報。"""

    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Number of items per page")
    total: int = Field(default=0, description="Total number of matching items")
    total_pages: int = Field(default=0, description="Total number of pages")


class MenuListResponse(BaseModel):
    """メニュー一覧 API のレスポンスモデル。"""

    menu_items: list[MenuItemResponse] = Field(
        default_factory=list,
        description="Menu items for the authenticated store",
    )
    pagination: MenuPaginationResponse = Field(
        default_factory=MenuPaginationResponse,
        description="Pagination metadata for the filtered menu items",
    )
