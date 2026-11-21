"""注文端末用カテゴリー一覧APIのHTTP応答とMySQL連携を検証する。"""

from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
)
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.responses.menu_category_response import (
    DeviceMenuCategoryListResponse,
    MenuCategoryDisplayResponse,
)


PATH = "/device/menu/categories"
DEVICE_UUID = "81006600-0000-4000-8000-000000000066"
EMPTY_STORE_DEVICE_UUID = "81006800-0000-4000-8000-000000000068"
JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"
CATEGORY_FIELDS = {"menu_category_id", "name", "image_url", "display_order"}


def _device_headers(device_uuid: str, expires_in: int = 300) -> dict[str, str]:
    """指定された端末用のJWTを署名し、Bearer認証ヘッダーを返す。"""
    token = DeviceAuthUtil.create_access_token(device_uuid, DeviceAuthConfig(JWT_SECRET, expires_in))
    return {"Authorization": f"Bearer {token}"}


class TestGetMenuCategories:
    """端末用カテゴリー一覧の入力、認証、HTTP応答を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("visit_session_id", [1, 9_223_372_036_854_775_807])
    @patch("app.dependencies.device_auth.get_device_auth_config", return_value=DeviceAuthConfig(JWT_SECRET, 300))
    @patch("app.endpoints.device.DeviceController.get_menu_categories")
    def test_returns_categories_with_no_store_header(self, get_categories, get_config, client, visit_session_id) -> None:
        """有効範囲の境界値を受理し、キャッシュ禁止付きで一覧を返す。

        Args:
            get_categories: カテゴリー取得Controllerのモック。
            get_config: 端末認証設定のモック。
            client: DBを使わないHTTPクライアント。
            visit_session_id: 許容範囲の端の来店セッションID。

        Returns:
            なし。
        """
        category = MenuCategoryDisplayResponse(
            menu_category_id=1,
            name="フード",
            image_url="https://example.com/categories/110/1.png",
            display_order=1,
        )
        result = DeviceMenuCategoryListResponse(menu_categories=[category])
        get_categories.return_value = result

        response = client.get(PATH, params={"visit_session_id": visit_session_id}, headers=_device_headers(DEVICE_UUID))

        assert response.status_code == 200
        assert response.json() == result.model_dump()
        assert response.headers["Cache-Control"] == "no-store"
        get_config.assert_called_once_with()
        get_categories.assert_called_once_with(device_uuid=DEVICE_UUID, visit_session_id=visit_session_id)

    @pytest.mark.parametrize("value", [None, "", "0", "-1", "1.0", "1_000", "1e2", "9223372036854775808"])
    @patch("app.endpoints.device.DeviceController.get_menu_categories")
    def test_rejects_invalid_session_id(self, get_categories, client, value) -> None:
        """不正な来店セッションIDを値の転載なしで拒否する。

        Args:
            get_categories: カテゴリー取得Controllerのモック。
            client: DBを使わないHTTPクライアント。
            value: 不正なクエリ値。Noneの場合は未指定。

        Returns:
            なし。
        """
        params = {} if value is None else {"visit_session_id": value}

        response = client.get(PATH, params=params)

        assert response.status_code == 422
        [error] = response.json()["detail"]
        assert error["loc"] == ["query", "visit_session_id"]
        assert set(error) == {"loc", "type", "msg"}
        get_categories.assert_not_called()

    @pytest.mark.parametrize(
        "headers",
        [{}, {"Authorization": "Basic invalid"}, {"Authorization": "Bearer invalid"}, _device_headers(DEVICE_UUID, -60)],
    )
    @patch("app.dependencies.device_auth.get_device_auth_config", return_value=DeviceAuthConfig(JWT_SECRET, 300))
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rejects_invalid_token_before_database(self, get_mysql_db, get_config, client, headers) -> None:
        """無効なBearer認証ではDBに接続せず401を返す。

        Args:
            get_mysql_db: MySQL接続のモック。
            get_config: 端末認証設定のモック。
            client: DBを使わないHTTPクライアント。
            headers: 未指定、不正または期限切れを再現するHTTPヘッダー。

        Returns:
            なし。
        """
        response = client.get(PATH, params={"visit_session_id": 820066}, headers=headers)

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"]["message"] == DEVICE_AUTHENTICATION_FAILED_ERROR
        if headers.get("Authorization", "").startswith("Bearer "):
            get_config.assert_called_once_with()
        else:
            get_config.assert_not_called()
        get_mysql_db.assert_not_called()

    @patch("app.dependencies.device_auth.get_device_auth_config", side_effect=ValueError("auth settings"))
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_reports_auth_config_failure(self, get_mysql_db, get_config, client) -> None:
        """端末認証設定の取得に失敗した場合はDBに接続せず500を返す。

        Args:
            get_mysql_db: MySQL接続のモック。
            get_config: 取得できない認証設定のモック。
            client: DBを使わないHTTPクライアント。

        Returns:
            なし。
        """
        response = client.get(PATH, params={"visit_session_id": 820066}, headers=_device_headers(DEVICE_UUID))

        assert response.status_code == 500
        assert response.json()["detail"] == {"status": "error", "message": SERVER_ERROR}
        get_config.assert_called_once_with()
        get_mysql_db.assert_not_called()

    @pytest.mark.usefixtures("insert_device_menu_categories", "initialize_ssm")
    def test_with_db_returns_only_visible_categories_in_display_order(self, client_with_db) -> None:
        """所属店舗の有効・未削除カテゴリーと署名付き画像URLを表示順で返す。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(PATH, params={"visit_session_id": 820066}, headers=_device_headers(DEVICE_UUID))

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        payload = response.json()
        assert set(payload) == {"menu_categories"}
        categories = payload["menu_categories"]
        assert [(item["menu_category_id"], item["name"], item["display_order"]) for item in categories] == [
            (830012, "フード", 1),
            (830013, "デザート", 1),
            (830011, "ドリンク", 2),
        ]
        for item, extension in zip(categories, ["jpg", "png", "png"], strict=True):
            assert set(item) == CATEGORY_FIELDS
            image_url = urlsplit(item["image_url"])
            assert image_url.path == f"/categories/110/{item['menu_category_id']}.{extension}"
            assert {"Signature", "X-Amz-Signature"} & parse_qs(image_url.query).keys()

    @pytest.mark.usefixtures("insert_visit_session_data")
    @patch("app.helpers.menu_category_image_helper.SsmClient")
    def test_with_db_returns_empty_list_without_image_config(self, get_ssm, client_with_db) -> None:
        """対象店舗にカテゴリーがなければ画像設定を取得せず空配列を返す。

        Args:
            get_ssm: 画像設定のモック。
            client_with_db: MySQLに接続するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(
            PATH,
            params={"visit_session_id": 820068},
            headers=_device_headers(EMPTY_STORE_DEVICE_UUID),
        )

        assert response.status_code == 200
        assert response.json() == {"menu_categories": []}
        assert response.headers["Cache-Control"] == "no-store"
        get_ssm.assert_not_called()

    @pytest.mark.usefixtures("insert_visit_session_data")
    @pytest.mark.parametrize(
        ("device_uuid", "visit_session_id"),
        [
            (DEVICE_UUID, 1),
            (DEVICE_UUID, 820068),
            ("81006100-0000-4000-8000-000000000061", 820068),
            ("81006200-0000-4000-8000-000000000062", 820062),
            ("81006500-0000-4000-8000-000000000065", 820065),
        ],
        ids=["missing", "other-store-device", "same-store-device", "closed", "checkout"],
    )
    def test_with_db_returns_404_for_unavailable_session(self, client_with_db, device_uuid, visit_session_id) -> None:
        """不存在、他端末、終了済み、決済処理中のセッションに同じ404を返す。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            device_uuid: アクセストークンを発行する端末UUID。
            visit_session_id: 利用できない来店セッションID。

        Returns:
            なし。
        """
        response = client_with_db.get(
            PATH, params={"visit_session_id": visit_session_id}, headers=_device_headers(device_uuid),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == {"status": "error", "message": VISIT_SESSION_NOT_FOUND_ERROR}

    @pytest.mark.usefixtures("insert_device_access_token_data")
    @pytest.mark.parametrize(
        "device_uuid",
        [
            "81005200-0000-4000-8000-000000000052",
            "81005300-0000-4000-8000-000000000053",
            "81005400-0000-4000-8000-000000000054",
            "81005900-0000-4000-8000-000000000059",
        ],
        ids=["stopped", "deleted", "unactivated", "missing"],
    )
    def test_with_db_rejects_unavailable_device(self, client_with_db, device_uuid) -> None:
        """有効なJWTでもDB上で利用できない端末は401で拒否する。

        Args:
            client_with_db: MySQLに接続するHTTPクライアント。
            device_uuid: 利用できない端末のUUID。

        Returns:
            なし。
        """
        response = client_with_db.get(PATH, params={"visit_session_id": 820066}, headers=_device_headers(device_uuid))

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"]["message"] == DEVICE_AUTHENTICATION_FAILED_ERROR
