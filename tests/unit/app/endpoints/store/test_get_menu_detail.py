"""メニュー詳細取得エンドポイントのテスト。"""

from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.responses.menu_detail_response import (
    MenuDetailResponse,
    MenuOptionGroupResponse,
    MenuOptionResponse,
)


class TestGetMenuDetail:
    """メニュー詳細取得エンドポイントを検証する。"""

    @patch("app.endpoints.store.StoreController.get_menu_detail")
    def test_returns_wrapped_menu_detail(
        self,
        mock_get_menu_detail,
        client,
    ) -> None:
        """Controllerの取得結果を共通レスポンス形式で返す。"""
        mock_get_menu_detail.return_value = MenuDetailResponse(
            menu_item_id=10,
            menu_category_id=1,
            menu_category_name="ハンバーガー",
            name="チーズバーガー",
            description="チェダーチーズ入り",
            price="800.000000",
            token_symbol="JPYC",
            image_url="https://example.com/menus/101/10.jpeg",
            is_available=True,
            display_order=1,
            option_groups=[
                MenuOptionGroupResponse(
                    menu_option_group_id=20,
                    name="サイズ",
                    min_selections=1,
                    max_selections=1,
                    display_order=1,
                    is_active=True,
                    options=[
                        MenuOptionResponse(
                            menu_option_id=30,
                            name="大盛り",
                            additional_price="100.000000",
                            display_order=1,
                            is_available=True,
                        )
                    ],
                )
            ],
        )

        response = client.get("/store/menu/10")

        assert response.status_code == 200
        assert response.json()["data"]["menu_item_id"] == 10
        assert response.json()["data"]["option_groups"][0]["options"] == [
            {
                "menu_option_id": 30,
                "name": "大盛り",
                "additional_price": "100.000000",
                "display_order": 1,
                "is_available": True,
            }
        ]
        mock_get_menu_detail.assert_called_once_with(
            store_id=101,
            menu_item_id=10,
        )

    @patch("app.endpoints.store.StoreController.get_menu_detail")
    def test_returns_http_exception_from_controller(
        self,
        mock_get_menu_detail,
        client,
    ) -> None:
        """Controllerが送出したHTTPExceptionをそのまま返す。"""
        mock_get_menu_detail.side_effect = HTTPException(
            status_code=404,
            detail={"status": "error", "message": "not found"},
        )

        response = client.get("/store/menu/999")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {"status": "error", "message": "not found"}
        }

    @pytest.mark.parametrize("menu_item_id", [0, -1, "invalid"])
    def test_returns_validation_error_for_invalid_id(
        self,
        client,
        menu_item_id,
    ) -> None:
        """不正なメニュー商品IDに422を返す。"""
        response = client.get(f"/store/menu/{menu_item_id}")

        assert response.status_code == 422

    @pytest.mark.usefixtures(
        "insert_menu_items",
        "initialize_ssm",
    )
    def test_with_db_returns_nested_menu_detail(
        self,
        store_client_with_db,
        mysql_session,
    ) -> None:
        """実DBの商品とオプションを階層レスポンスで返す。"""
        option_group = MenuOptionGroup(
            menu_option_group_id=131,
            menu_item_id=22,
            name="サイズ",
            min_selections=1,
            max_selections=1,
            display_order=1,
            is_active=False,
        )
        mysql_session.add(option_group)
        mysql_session.flush()
        mysql_session.add(
            MenuOption(
                menu_option_id=141,
                menu_option_group_id=131,
                name="大盛り",
                additional_price=100,
                display_order=1,
                is_available=False,
            )
        )
        mysql_session.commit()

        response = store_client_with_db.get("/store/menu/22")

        assert response.status_code == 200
        detail = response.json()["data"]
        assert detail["menu_item_id"] == 22
        assert detail["menu_category_name"] == "ドリンク"
        assert detail["is_available"] is False
        assert detail["option_groups"] == [
            {
                "menu_option_group_id": 131,
                "name": "サイズ",
                "min_selections": 1,
                "max_selections": 1,
                "display_order": 1,
                "is_active": False,
                "options": [
                    {
                        "menu_option_id": 141,
                        "name": "大盛り",
                        "additional_price": "100.000000",
                        "display_order": 1,
                        "is_available": False,
                    }
                ],
            }
        ]
        assert "/menus/101/22.png" in detail["image_url"]

    @pytest.mark.usefixtures("insert_menu_items")
    @pytest.mark.parametrize("menu_item_id", [25, 26, 999])
    def test_with_db_returns_not_found(
        self,
        store_client_with_db,
        menu_item_id,
    ) -> None:
        """削除済み、別店舗、未存在の商品に404を返す。"""
        response = store_client_with_db.get(f"/store/menu/{menu_item_id}")

        assert response.status_code == 404
