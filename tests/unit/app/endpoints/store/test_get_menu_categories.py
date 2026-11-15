from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.responses.menu_category_response import (
    MenuCategoryListResponse,
    MenuCategoryPaginationResponse,
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
        """controllerの取得結果を共通レスポンス形式で返すことを確認する。"""
        mock_get_menu_categories.return_value = MenuCategoryListResponse(
            menu_categories=[
                MenuCategoryResponse(
                    menu_category_id=1,
                    name="ハンバーガー",
                    image_url="https://example.com/categories/101/1.png",
                    display_order=1,
                    is_active=True,
                ),
                MenuCategoryResponse(
                    menu_category_id=2,
                    name="ドリンク",
                    image_url="https://example.com/categories/101/2.png",
                    display_order=2,
                    is_active=True,
                ),
            ],
            pagination=MenuCategoryPaginationResponse(
                page=1,
                page_size=None,
                total=2,
                total_pages=1,
            ),
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
                        "image_url": "https://example.com/categories/101/1.png",
                        "display_order": 1,
                        "is_active": True,
                    },
                    {
                        "menu_category_id": 2,
                        "name": "ドリンク",
                        "image_url": "https://example.com/categories/101/2.png",
                        "display_order": 2,
                        "is_active": True,
                    },
                ],
                "pagination": {
                    "page": 1,
                    "page_size": None,
                    "total": 2,
                    "total_pages": 1,
                },
            },
        }
        mock_get_menu_categories.assert_called_once_with(
            store_id=101,
            name=None,
            is_active=True,
            page=1,
            page_size=None,
        )

    @patch("app.endpoints.store.StoreController.get_menu_categories")
    def test_returns_http_exception_from_controller(
        self,
        mock_get_menu_categories,
        client,
    ) -> None:
        """controllerが送出したHTTPExceptionをそのまま返すことを確認する。"""
        mock_get_menu_categories.side_effect = HTTPException(
            status_code=500,
            detail={"status": "error", "message": "server error"},
        )

        response = client.get("/store/menu/categories")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {"status": "error", "message": "server error"}
        }

    @pytest.mark.usefixtures("insert_menu_categories", "initialize_ssm")
    def test_with_db(self, store_client_with_db) -> None:
        """DB 連携時に認証済み店舗の有効なカテゴリーを表示順で返すことを確認する。"""
        response = store_client_with_db.get("/store/menu/categories")

        assert response.status_code == 200
        categories = response.json()["data"]["menu_categories"]
        assert [
            (category["menu_category_id"], category["name"], category["display_order"])
            for category in categories
        ] == [
            (12, "フード", 1),
            (13, "デザート", 1),
            (11, "ドリンク", 2),
        ]
        for category in categories:
            expected_path = f"/categories/101/{category['menu_category_id']}.png"
            assert expected_path in category["image_url"]
            assert category["is_active"] is True
        assert response.json()["data"]["pagination"] == {
            "page": 1,
            "page_size": None,
            "total": 3,
            "total_pages": 1,
        }

    @pytest.mark.usefixtures("insert_menu_categories", "initialize_ssm")
    def test_with_db_filters_by_name_status_and_paginates(
        self,
        store_client_with_db,
    ) -> None:
        response = store_client_with_db.get(
            "/store/menu/categories",
            params={
                "name": "カテゴリー",
                "is_active": False,
                "page": 1,
                "page_size": 1,
            },
        )

        assert response.status_code == 200
        response_data = response.json()["data"]
        assert len(response_data["menu_categories"]) == 1
        category = response_data["menu_categories"][0]
        assert category["menu_category_id"] == 14
        assert category["is_active"] is False
        assert response_data["pagination"] == {
            "page": 1,
            "page_size": 1,
            "total": 1,
            "total_pages": 1,
        }

    @pytest.mark.usefixtures("insert_menu_categories", "initialize_ssm")
    def test_with_db_returns_requested_page(self, store_client_with_db) -> None:
        response = store_client_with_db.get(
            "/store/menu/categories",
            params={"page": 2, "page_size": 1},
        )

        assert response.status_code == 200
        response_data = response.json()["data"]
        assert [
            category["menu_category_id"]
            for category in response_data["menu_categories"]
        ] == [13]
        assert response_data["pagination"] == {
            "page": 2,
            "page_size": 1,
            "total": 3,
            "total_pages": 3,
        }

    @pytest.mark.parametrize(
        "params",
        [
            {"page": 0},
            {"page_size": 0},
            {"page_size": 101},
            {"name": ""},
        ],
    )
    def test_returns_validation_error_for_invalid_search_params(
        self,
        client,
        params,
    ) -> None:
        response = client.get("/store/menu/categories", params=params)

        assert response.status_code == 422

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
            "data": {
                "menu_categories": [],
                "pagination": {
                    "page": 1,
                    "page_size": None,
                    "total": 0,
                    "total_pages": 0,
                },
            },
        }
