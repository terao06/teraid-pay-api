"""メニュー基本情報更新エンドポイントのテスト。"""

from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_item import MenuItem
from app.models.responses.menu_update_response import MenuUpdateResponse


MENU_UPDATE_REQUEST = {
    "menu_category_id": 12,
    "name": "更新商品",
    "description": "更新後の説明",
    "price": "950.000000",
    "token_symbol": "JPYC",
    "is_available": False,
    "display_order": 3,
}


class TestUpdateMenu:
    """メニュー基本情報更新エンドポイントを検証する。"""

    @patch("app.endpoints.store.StoreController.update_menu")
    def test_returns_wrapped_updated_menu(
        self,
        mock_update_menu,
        client,
    ) -> None:
        """Controllerの更新結果を共通レスポンス形式で返す。"""
        mock_update_menu.return_value = MenuUpdateResponse(
            menu_item_id=21,
        )

        response = client.put("/store/menu/21", json=MENU_UPDATE_REQUEST)

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_item_id": 21,
            },
        }
        request = mock_update_menu.call_args.kwargs["request"]
        assert mock_update_menu.call_args.kwargs["store_id"] == 101
        assert mock_update_menu.call_args.kwargs["menu_item_id"] == 21
        assert request.name == "更新商品"
        assert request.menu_image is None
        assert request.image_extension is None

    @patch("app.endpoints.store.StoreController.update_menu")
    def test_returns_http_exception_from_controller(
        self,
        mock_update_menu,
        client,
    ) -> None:
        """Controllerが送出したHTTPExceptionをそのまま返す。"""
        mock_update_menu.side_effect = HTTPException(
            status_code=404,
            detail={"status": "error", "message": "not found"},
        )

        response = client.put("/store/menu/999", json=MENU_UPDATE_REQUEST)

        assert response.status_code == 404
        assert response.json() == {
            "detail": {"status": "error", "message": "not found"}
        }

    @pytest.mark.parametrize(
        ("menu_item_id", "request_json"),
        [
            (0, MENU_UPDATE_REQUEST),
            (21, {**MENU_UPDATE_REQUEST, "name": ""}),
            (21, {**MENU_UPDATE_REQUEST, "price": "-1"}),
            (21, {**MENU_UPDATE_REQUEST, "display_order": -1}),
            (21, {**MENU_UPDATE_REQUEST, "menu_image": "image"}),
            (21, {**MENU_UPDATE_REQUEST, "image_extension": "png"}),
            (21, {**MENU_UPDATE_REQUEST, "option_groups": []}),
        ],
    )
    def test_returns_validation_error(
        self,
        client,
        menu_item_id,
        request_json,
    ) -> None:
        """不正なパス、商品情報、画像指定、余分な項目に422を返す。"""
        response = client.put(
            f"/store/menu/{menu_item_id}",
            json=request_json,
        )

        assert response.status_code == 422

    @pytest.mark.usefixtures("insert_menu_items")
    def test_with_db_updates_only_menu_basic_information(
        self,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """実DBの商品基本情報を画像とオプションに触れず更新する。"""
        item = (
            mysql_session.query(MenuItem)
            .filter(MenuItem.menu_item_id == 22)
            .one()
        )
        original_state = {
            "menu_category_id": item.menu_category_id,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "token_symbol": item.token_symbol,
            "image_extension": item.image_extension,
            "is_available": item.is_available,
            "display_order": item.display_order,
        }
        try:
            response = store_client_with_db.put(
                "/store/menu/22",
                json=MENU_UPDATE_REQUEST,
            )

            assert response.status_code == 200
            assert response.json()["data"] == {
                "menu_item_id": 22,
            }
            mysql_session.rollback()
            mysql_session.expire_all()
            updated_item = (
                mysql_session.query(MenuItem)
                .filter(MenuItem.menu_item_id == 22)
                .one()
            )
            assert updated_item.name == "更新商品"
            assert updated_item.image_extension == original_state["image_extension"]
        finally:
            mysql_session.rollback()
            mysql_session.expire_all()
            item = (
                mysql_session.query(MenuItem)
                .filter(MenuItem.menu_item_id == 22)
                .one()
            )
            for field_name, value in original_state.items():
                setattr(item, field_name, value)
            mysql_session.commit()

    @pytest.mark.usefixtures("insert_menu_items")
    @pytest.mark.parametrize("menu_item_id", [25, 26, 999])
    def test_with_db_returns_not_found(
        self,
        store_client_with_db,
        menu_item_id,
    ) -> None:
        """削除済み、別店舗、未存在の商品に404を返す。"""
        response = store_client_with_db.put(
            f"/store/menu/{menu_item_id}",
            json=MENU_UPDATE_REQUEST,
        )

        assert response.status_code == 404
