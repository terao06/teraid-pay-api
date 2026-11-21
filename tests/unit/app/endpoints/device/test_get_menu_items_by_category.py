"""カテゴリー別メニュー取得APIのHTTP応答とMySQL連携を検証する。"""

from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    MENU_CATEGORY_NOT_FOUND_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
)
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.responses.device_menu_item_list_response import DeviceMenuItemListResponse


PATH = "/device/menu/categories/{category_id}/items"
DEVICE_UUID = "86100100-0000-4000-8000-000000861001"
JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"
MAX_ID = 9_223_372_036_854_775_807
SESSION_ID = 862001
STORE_ID = 111


def _device_headers(expires_in: int = 300) -> dict[str, str]:
    """登録済み端末用のBearer認証ヘッダーを生成する。"""
    token = DeviceAuthUtil.create_access_token(DEVICE_UUID, DeviceAuthConfig(JWT_SECRET, expires_in))
    return {"Authorization": f"Bearer {token}"}


class TestGetMenuItemsByCategory:
    """端末向けの入力、認証、HTTP応答、MySQL連携を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("identifier", [1, MAX_ID])
    @patch("app.dependencies.device_auth.get_device_auth_config", return_value=DeviceAuthConfig(JWT_SECRET, 300))
    @patch("app.endpoints.device.DeviceController.get_menu_items_by_category")
    def test_accepts_positive_bigint_ids(self, get_items, get_config, client, identifier) -> None:
        """両IDの境界値を受理し、成功レスポンスにキャッシュ禁止を付ける。

        Args:
            get_items: Controllerのモック。
            get_config: JWT設定のモック。
            client: HTTPクライアント。
            identifier: 両IDに指定する境界値。

        Returns:
            なし。
        """
        get_items.return_value = DeviceMenuItemListResponse(menu_items=[])
        response = client.get(
            PATH.format(category_id=identifier), params={"visit_session_id": identifier}, headers=_device_headers(),
        )
        assert response.status_code == 200
        assert response.json() == {"menu_items": []}
        assert response.headers["Cache-Control"] == "no-store"
        get_config.assert_called_once_with()
        get_items.assert_called_once_with(
            device_uuid=DEVICE_UUID, visit_session_id=identifier, menu_category_id=identifier,
        )

    @pytest.mark.parametrize("value", ["0", "-1", "1.0", "1_000", "1e2", "１２", str(MAX_ID + 1)])
    @pytest.mark.parametrize(("location", "field"), [("path", "menu_category_id"), ("query", "visit_session_id")])
    @patch("app.endpoints.device.DeviceController.get_menu_items_by_category")
    def test_rejects_invalid_ids_without_echoing_input(self, get_items, client, location, field, value) -> None:
        """不正なIDを、入力値を転載せずに拒否する。

        Args:
            get_items: Controllerのモック。
            client: HTTPクライアント。
            location: 不正値の入力位置。
            field: 不正なフィールド名。
            value: 不正値。

        Returns:
            なし。
        """
        category_id = value if location == "path" else 1
        session_id = value if location == "query" else 1
        response = client.get(PATH.format(category_id=category_id), params={"visit_session_id": session_id})
        assert response.status_code == 422
        [error] = response.json()["detail"]
        assert error["loc"] == [location, field]
        assert set(error) == {"loc", "type", "msg"}
        get_items.assert_not_called()

    def test_rejects_missing_session_id(self, client) -> None:
        """必須クエリが省略された場合は422を返す。

        Args:
            client: HTTPクライアント。

        Returns:
            なし。
        """
        response = client.get(PATH.format(category_id=1))
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["query", "visit_session_id"]

    @pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}, _device_headers(-60)])
    @patch("app.dependencies.device_auth.get_device_auth_config", return_value=DeviceAuthConfig(JWT_SECRET, 300))
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rejects_invalid_token_before_mysql(self, get_mysql_db, get_config, client, headers) -> None:
        """Bearer認証に失敗した要求を、DBに接続せず401で拒否する。

        Args:
            get_mysql_db: DB接続のモック。
            get_config: JWT設定のモック。
            client: HTTPクライアント。
            headers: 認証に失敗するヘッダー。

        Returns:
            なし。
        """
        response = client.get(PATH.format(category_id=1), params={"visit_session_id": 1}, headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"] == {"status": "error", "message": DEVICE_AUTHENTICATION_FAILED_ERROR}
        assert get_config.called == bool(headers)
        get_mysql_db.assert_not_called()

    @pytest.mark.usefixtures("insert_device_menu_items", "initialize_ssm")
    def test_with_db_returns_ordered_items_options_and_signed_urls(self, client_with_db) -> None:
        """販売・選択可能なデータのみを並べ、署名付き画像URLを返す。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(
            PATH.format(category_id=860012), params={"visit_session_id": SESSION_ID}, headers=_device_headers(),
        )
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert set(response.json()) == {"menu_items"}
        items = response.json()["menu_items"]
        assert [(item["menu_item_id"], item["display_order"]) for item in items] == [
            (863012, 1), (863013, 1), (863011, 2),
        ]
        assert items[0]["name"] == "チーズバーガー"
        assert items[0]["price"] == "650.250000"
        assert items[0]["token_symbol"] == "JPYC"
        for item, extension in zip(items, ["jpeg", "jpg", "png"], strict=True):
            assert set(item) == {
                "menu_item_id", "name", "price", "token_symbol", "image_url", "display_order", "option_groups",
            }
            image = urlsplit(item["image_url"])
            assert image.path == f"/menus/{STORE_ID}/{item['menu_item_id']}.{extension}"
            assert {"Signature", "X-Amz-Signature"} & parse_qs(image.query).keys()
        size, toppings, sauces = items[0]["option_groups"]
        assert [
            (group["menu_option_group_id"], group["min_selections"], group["max_selections"], group["display_order"])
            for group in (size, toppings, sauces)
        ] == [(864115, 1, 1, 0), (864111, 0, 2, 1), (864112, 0, 1, 1)]
        assert [option["menu_option_id"] for option in size["options"]] == [865217]
        assert toppings["options"][0] == {
            "menu_option_id": 865212, "name": "チーズ追加", "additional_price": "100.500000", "display_order": 1,
        }
        assert [option["menu_option_id"] for option in toppings["options"]] == [865212, 865213, 865211]
        assert sauces["options"] == []
        assert items[1]["option_groups"] == items[2]["option_groups"] == []

    @pytest.mark.usefixtures("insert_device_menu_items")
    @patch("app.services.device_service.SsmClient")
    def test_with_db_returns_empty_list_without_loading_image_settings(self, ssm, client_with_db) -> None:
        """販売可能な商品がなければ200と空配列を返す。

        Args:
            ssm: 商品画像設定のモック。
            client_with_db: MySQLに接続するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(
            PATH.format(category_id=860013), params={"visit_session_id": SESSION_ID}, headers=_device_headers(),
        )
        assert response.status_code == 200
        assert response.json() == {"menu_items": []}
        assert response.headers["Cache-Control"] == "no-store"
        ssm.assert_not_called()

    @pytest.mark.usefixtures("insert_device_menu_items")
    @pytest.mark.parametrize(
        ("category_id", "session_id", "message"),
        [
            (860016, SESSION_ID, MENU_CATEGORY_NOT_FOUND_ERROR),
            (860014, SESSION_ID, MENU_CATEGORY_NOT_FOUND_ERROR),
            (860015, SESSION_ID, MENU_CATEGORY_NOT_FOUND_ERROR),
            (999999, SESSION_ID, MENU_CATEGORY_NOT_FOUND_ERROR),
            (860012, 862002, VISIT_SESSION_NOT_FOUND_ERROR),
        ],
        ids=["other-store", "inactive-category", "deleted-category", "missing-category", "other-device-session"],
    )
    def test_with_db_rejects_unavailable_category_or_session(self, client_with_db, category_id, session_id, message) -> None:
        """対象外のカテゴリーや来店セッションに404を返す。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            category_id: 指定カテゴリーID。
            session_id: 指定セッションID。
            message: 想定するエラーメッセージ。

        Returns:
            なし。
        """
        response = client_with_db.get(
            PATH.format(category_id=category_id), params={"visit_session_id": session_id}, headers=_device_headers(),
        )
        assert response.status_code == 404
        assert response.json()["detail"] == {"status": "error", "message": message}

    @pytest.mark.usefixtures("insert_device_menu_items")
    @patch("app.services.device_service.SsmClient", side_effect=RuntimeError("image settings"))
    def test_with_db_returns_500_when_image_settings_fail(self, ssm, client_with_db) -> None:
        """商品画像設定の取得に失敗した場合は共通形式の500を返す。

        Args:
            ssm: 取得に失敗する画像設定のモック。
            client_with_db: MySQLに接続するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(
            PATH.format(category_id=860012), params={"visit_session_id": SESSION_ID}, headers=_device_headers(),
        )
        assert response.status_code == 500
        assert response.json()["detail"] == {"status": "error", "message": SERVER_ERROR}
        ssm.assert_called_once_with()
