"""メニューカテゴリー詳細取得エンドポイントのテスト。"""

from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.responses.menu_category_response import MenuCategoryResponse


class TestGetMenuCategory:
    """メニューカテゴリー詳細取得エンドポイントを検証する。"""

    @patch("app.endpoints.store.StoreController.get_menu_category")
    def test_returns_wrapped_menu_category(
        self,
        mock_get_menu_category,
        client,
    ) -> None:
        """Controllerの取得結果を共通レスポンス形式で返す。"""
        mock_get_menu_category.return_value = MenuCategoryResponse(
            menu_category_id=14,
            name="無効カテゴリー",
            image_url="https://example.com/categories/101/14.png",
            display_order=0,
            is_active=False,
        )

        response = client.get("/store/menu/categories/14")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_category_id": 14,
                "name": "無効カテゴリー",
                "image_url": "https://example.com/categories/101/14.png",
                "display_order": 0,
                "is_active": False,
            },
        }
        mock_get_menu_category.assert_called_once_with(
            store_id=101,
            menu_category_id=14,
        )

    @patch("app.endpoints.store.StoreController.get_menu_category")
    def test_returns_http_exception_from_controller(
        self,
        mock_get_menu_category,
        client,
    ) -> None:
        """Controllerが送出したHTTPExceptionをそのまま返す。"""
        mock_get_menu_category.side_effect = HTTPException(
            status_code=404,
            detail={"status": "error", "message": "not found"},
        )

        response = client.get("/store/menu/categories/999")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {"status": "error", "message": "not found"}
        }

    @pytest.mark.parametrize("menu_category_id", [0, -1, "invalid"])
    def test_returns_validation_error_for_invalid_id(
        self,
        client,
        menu_category_id,
    ) -> None:
        """不正なカテゴリーIDに422を返す。"""
        response = client.get(f"/store/menu/categories/{menu_category_id}")

        assert response.status_code == 422

    @pytest.mark.usefixtures("insert_menu_categories", "initialize_ssm")
    def test_with_db_returns_inactive_category(self, store_client_with_db) -> None:
        """認証店舗の無効カテゴリーも詳細取得できる。"""
        response = store_client_with_db.get("/store/menu/categories/14")

        assert response.status_code == 200
        category = response.json()["data"]
        assert category["menu_category_id"] == 14
        assert category["is_active"] is False
        assert "/categories/101/14.png" in category["image_url"]

    @pytest.mark.usefixtures("insert_menu_categories")
    @pytest.mark.parametrize("menu_category_id", [15, 16, 999])
    def test_with_db_returns_not_found(
        self,
        store_client_with_db,
        menu_category_id,
    ) -> None:
        """削除済み、他店舗、未存在のカテゴリーに404を返す。"""
        response = store_client_with_db.get(
            f"/store/menu/categories/{menu_category_id}"
        )

        assert response.status_code == 404
