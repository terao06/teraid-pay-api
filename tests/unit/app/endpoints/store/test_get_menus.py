from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.responses.menu_list_response import (
    MenuItemResponse,
    MenuListResponse,
    MenuPaginationResponse,
)


class TestGetMenus:
    """メニュー一覧取得エンドポイントの単体テスト。"""

    @patch("app.endpoints.store.StoreController.get_menus")
    def test_returns_wrapped_menus(
        self,
        mock_get_menus,
        client,
    ) -> None:
        """controllerの取得結果を共通レスポンス形式で返すことを確認する。"""
        mock_get_menus.return_value = MenuListResponse(
            menu_items=[
                MenuItemResponse(
                    menu_item_id=10,
                    menu_category_id=1,
                    menu_category_name="ハンバーガー",
                    name="チーズバーガー",
                    description="チェダーチーズ入り",
                    price="800.000000",
                    token_symbol="JPYC",
                    image_url="https://s3.example.com/menus/101/10.jpeg",
                    is_available=True,
                    display_order=1,
                )
            ],
            pagination=MenuPaginationResponse(
                page=1,
                page_size=20,
                total=1,
                total_pages=1,
            ),
        )

        response = client.get("/store/menu")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_items": [
                    {
                        "menu_item_id": 10,
                        "menu_category_id": 1,
                        "menu_category_name": "ハンバーガー",
                        "name": "チーズバーガー",
                        "description": "チェダーチーズ入り",
                        "price": "800.000000",
                        "token_symbol": "JPYC",
                        "image_url": "https://s3.example.com/menus/101/10.jpeg",
                        "is_available": True,
                        "display_order": 1,
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "total_pages": 1,
                },
            },
        }
        mock_get_menus.assert_called_once_with(
            store_id=101,
            name=None,
            menu_category_id=None,
            is_available=None,
            page=1,
            page_size=20,
        )

    @patch("app.endpoints.store.StoreController.get_menus")
    def test_forwards_search_parameters(
        self,
        mock_get_menus,
        client,
    ) -> None:
        """指定された検索条件をcontrollerへ渡すことを確認する。"""
        mock_get_menus.return_value = MenuListResponse(menu_items=[])

        response = client.get(
            "/store/menu",
            params={
                "name": "バーガー",
                "menu_category_id": 12,
                "is_available": False,
                "page": 2,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        mock_get_menus.assert_called_once_with(
            store_id=101,
            name="バーガー",
            menu_category_id=12,
            is_available=False,
            page=2,
            page_size=10,
        )

    @patch("app.endpoints.store.StoreController.get_menus")
    def test_returns_http_exception_from_controller(
        self,
        mock_get_menus,
        client,
    ) -> None:
        """controllerが送出したHTTPExceptionをそのまま返すことを確認する。"""
        mock_get_menus.side_effect = HTTPException(
            status_code=500,
            detail={"status": "error", "message": "server error"},
        )

        response = client.get("/store/menu")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {"status": "error", "message": "server error"}
        }

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @pytest.mark.usefixtures("insert_menu_items")
    def test_with_db(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        store_client_with_db,
    ) -> None:
        """DB 連携時に認証済み店舗の未削除商品を表示順で返すことを確認する。"""
        mock_ssm_client_class.return_value.s3_endpoint = "http://s3.local"
        mock_ssm_client_class.return_value.menu_image_bucket = "menus"
        mock_ssm_client_class.return_value.menu_image_url_expires_in = 3600
        mock_s3_client_class.return_value.generate_presigned_get_url.side_effect = (
            lambda bucket_name, file_name, expires_in: (
                f"https://s3.example.com/{bucket_name}/{file_name}"
            )
        )

        response = store_client_with_db.get("/store/menu")

        assert response.status_code == 200
        response_body = response.json()
        assert response_body["status"] == "success"
        menu_items = response_body["data"]["menu_items"]
        fixture_menu_items = [
            menu_item
            for menu_item in menu_items
            if menu_item["menu_item_id"] in {21, 22, 23, 24}
        ]
        assert fixture_menu_items == [
            {
                "menu_item_id": 21,
                "menu_category_id": 12,
                "menu_category_name": "フード",
                "name": "チーズバーガー",
                "description": "チェダーチーズ入り",
                "price": "800.000000",
                "token_symbol": "JPYC",
                "image_url": "https://s3.example.com/menus/101/21.jpeg",
                "is_available": True,
                "display_order": 1,
            },
            {
                "menu_item_id": 22,
                "menu_category_id": 11,
                "menu_category_name": "ドリンク",
                "name": "コーラ",
                "description": None,
                "price": "200.000000",
                "token_symbol": "JPYC",
                "image_url": "https://s3.example.com/menus/101/22.png",
                "is_available": False,
                "display_order": 1,
            },
            {
                "menu_item_id": 23,
                "menu_category_id": None,
                "menu_category_name": None,
                "name": "旧カテゴリー商品",
                "description": None,
                "price": "500.000000",
                "token_symbol": "JPYC",
                "image_url": "https://s3.example.com/menus/101/23.jpg",
                "is_available": True,
                "display_order": 2,
            },
            {
                "menu_item_id": 24,
                "menu_category_id": None,
                "menu_category_name": None,
                "name": "未分類商品",
                "description": None,
                "price": "300.000000",
                "token_symbol": "JPYC",
                "image_url": "https://s3.example.com/menus/101/24.png",
                "is_available": True,
                "display_order": 3,
            },
        ]
        menu_item_ids = [menu_item["menu_item_id"] for menu_item in menu_items]
        assert 25 not in menu_item_ids
        assert 26 not in menu_item_ids

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @pytest.mark.usefixtures("insert_menu_items")
    def test_with_db_returns_empty_list_when_not_found(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        store_client_with_db_without_wallet_manager,
    ) -> None:
        """DB 連携時に商品が存在しない場合は空配列を返すことを確認する。"""
        response = store_client_with_db_without_wallet_manager.get("/store/menu")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_items": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total": 0,
                    "total_pages": 0,
                },
            },
        }
        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()
