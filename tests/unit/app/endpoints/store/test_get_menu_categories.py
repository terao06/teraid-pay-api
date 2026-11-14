from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.responses.menu_category_response import (
    MenuCategoryListResponse,
    MenuCategoryResponse,
)


class TestGetMenuCategories:
    """メニューカテゴリー取得エンドポイントの単体テスト。"""

    @patch("app.endpoints.store.StoreController.get_menu_categories")
    def test_returns_wrapped_menu_categories(
        self,
        mock_get_menu_categories,
        client,
    ) -> None:
        mock_get_menu_categories.return_value = MenuCategoryListResponse(
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

        response = client.get("/store/menu/categories")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_categories": [
                    {
                        "menu_category_id": 1,
                        "name": "ハンバーガー",
                        "display_order": 1,
                    },
                    {
                        "menu_category_id": 2,
                        "name": "ドリンク",
                        "display_order": 2,
                    },
                ]
            },
        }
        mock_get_menu_categories.assert_called_once_with(store_id=101)

    @patch("app.endpoints.store.StoreController.get_menu_categories")
    def test_returns_http_exception_from_controller(
        self,
        mock_get_menu_categories,
        client,
    ) -> None:
        mock_get_menu_categories.side_effect = HTTPException(
            status_code=500,
            detail={"status": "error", "message": "server error"},
        )

        response = client.get("/store/menu/categories")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {"status": "error", "message": "server error"}
        }

    @pytest.mark.usefixtures("insert_menu_categories")
    def test_with_db(self, store_client_with_db) -> None:
        """DB 連携時に認証済み店舗の有効なカテゴリーを表示順で返すことを確認する。"""
        response = store_client_with_db.get("/store/menu/categories")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_categories": [
                    {
                        "menu_category_id": 12,
                        "name": "フード",
                        "display_order": 1,
                    },
                    {
                        "menu_category_id": 13,
                        "name": "デザート",
                        "display_order": 1,
                    },
                    {
                        "menu_category_id": 11,
                        "name": "ドリンク",
                        "display_order": 2,
                    },
                ]
            },
        }

    @pytest.mark.usefixtures("insert_menu_categories")
    def test_with_db_returns_empty_list_when_not_found(
        self,
        store_client_with_db_without_wallet_manager,
    ) -> None:
        """DB 連携時にカテゴリーが存在しない場合は空配列を返すことを確認する。"""
        response = store_client_with_db_without_wallet_manager.get(
            "/store/menu/categories"
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {"menu_categories": []},
        }
