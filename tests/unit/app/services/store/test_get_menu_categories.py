from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.models.responses.menu_category_response import (
    MenuCategoryListResponse,
    MenuCategoryResponse,
)
from app.services.store_service import StoreService


class TestGetMenuCategories:
    """StoreService のメニューカテゴリー取得処理を検証する。"""

    @patch("app.services.store_service.StoreRepository")
    def test_get_menu_categories(self, mock_repository_class) -> None:
        """取得したカテゴリーを一覧レスポンスへ変換することを確認する。"""
        mysql_session = Mock()
        mock_repository_class.return_value.get_active_menu_categories.return_value = [
            SimpleNamespace(menu_category_id=1, name="ハンバーガー", display_order=1),
            SimpleNamespace(menu_category_id=2, name="ドリンク", display_order=2),
        ]

        result = StoreService().get_menu_categories(
            mysql_session=mysql_session,
            store_id=101,
        )

        assert result == MenuCategoryListResponse(
            menu_categories=[
                MenuCategoryResponse(
                    menu_category_id=1,
                    name="ハンバーガー",
                    display_order=1,
                ),
                MenuCategoryResponse(
                    menu_category_id=2,
                    name="ドリンク",
                    display_order=2,
                ),
            ]
        )
        mock_repository_class.return_value.get_active_menu_categories.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )

    @patch("app.services.store_service.StoreRepository")
    def test_get_menu_categories_returns_empty_list(
        self,
        mock_repository_class,
    ) -> None:
        """カテゴリーが存在しない場合に空の一覧を返すことを確認する。"""
        mock_repository_class.return_value.get_active_menu_categories.return_value = []

        result = StoreService().get_menu_categories(
            mysql_session=Mock(),
            store_id=101,
        )

        assert result == MenuCategoryListResponse(menu_categories=[])
