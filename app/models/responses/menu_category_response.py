"""メニューカテゴリーAPIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class MenuCategoryDisplayResponse(BaseModel):
    """カテゴリー表示に必要な情報を表す。

    Args:
        menu_category_id: メニューカテゴリーID。
        name: カテゴリー名。
        image_url: カテゴリー画像の署名付きGET URL。
        display_order: 表示順。

    Returns:
        カテゴリー表示用のレスポンス要素。
    """

    menu_category_id: int = Field(..., description="Menu category ID")
    name: str = Field(..., description="Menu category name")
    image_url: str = Field(..., description="Presigned category image URL")
    display_order: int = Field(..., description="Display order")


class MenuCategoryResponse(MenuCategoryDisplayResponse):
    """メニューカテゴリーの表示情報と有効状態を表す。"""

    is_active: bool = Field(..., description="Active flag")


class DeviceMenuCategoryListResponse(BaseModel):
    """注文端末向けのメニューカテゴリー一覧を表す。

    Args:
        menu_categories: 所属店舗の有効なカテゴリーの表示順の一覧。

    Returns:
        カテゴリー一覧のレスポンス。
    """

    menu_categories: list[MenuCategoryDisplayResponse] = Field(
        description="Active menu categories for the authenticated device's store",
    )


class MenuCategoryCreateResponse(BaseModel):
    """登録したメニューカテゴリーIDを表す。"""

    menu_category_id: int = Field(..., description="Menu category ID")


class MenuCategoryUpdateResponse(BaseModel):
    """更新したメニューカテゴリーIDを表す。"""

    menu_category_id: int = Field(..., description="Menu category ID")


class MenuCategoryDeleteResponse(BaseModel):
    """論理削除したメニューカテゴリーの結果を表す。

    Args:
        menu_category_id: 削除したメニューカテゴリーID。

    Returns:
        削除したメニューカテゴリーIDを含むレスポンスモデル。
    """

    menu_category_id: int = Field(..., description="削除したメニューカテゴリーID")


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
