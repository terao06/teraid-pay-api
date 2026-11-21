"""端末の注文履歴をHTTPから検証する。"""

from unittest.mock import patch

import pytest

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import DEVICE_AUTHENTICATION_FAILED_ERROR, VISIT_SESSION_NOT_FOUND_ERROR
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.responses.device_order_history_response import DeviceOrderHistoryResponse


PATH = "/device/visit-sessions/{visit_id}/orders"
JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"


def _headers(device_id: int = 891001) -> dict[str, str]:
    """テスト用の端末UUIDで署名したBearerヘッダーを返す。"""
    device_uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
    token = DeviceAuthUtil.create_access_token(device_uuid, DeviceAuthConfig(JWT_SECRET, 300))
    return {"Authorization": f"Bearer {token}"}


class TestGetOrderHistory:
    """デバイス側注文履歴取得APIのHTTP契約を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("visit_id", ["0", "-1", "1.0", "１２", "9223372036854775808"])
    def test_rejects_invalid_session_id_before_mysql(self, client, visit_id) -> None:
        """不正なIDを反映せず、DB接続前に422を返す。

        Args:
            client: HTTPクライアント。
            visit_id: 不正な来店セッションID。

        Returns:
            なし。
        """
        with patch("app.middlewares.transaction.get_mysql_db") as mysql:
            response = client.get(PATH.format(visit_id=visit_id), headers=_headers())

        assert response.status_code == 422
        error = response.json()["detail"][0]
        assert error["loc"] == ["path", "visit_session_id"]
        assert "input" not in error
        mysql.assert_not_called()

    @pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
    def test_rejects_invalid_token_before_mysql(self, client, headers) -> None:
        """トークンの欠落・不正はDB接続前に401を返す。

        Args:
            client: HTTPクライアント。
            headers: 認証に失敗するリクエストヘッダー。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=DeviceAuthConfig(JWT_SECRET, 300)),
            patch("app.middlewares.transaction.get_mysql_db") as mysql,
        ):
            response = client.get(PATH.format(visit_id=892001), headers=headers)

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        mysql.assert_not_called()

    def test_accepts_maximum_bigint_and_disables_cache(self, client) -> None:
        """正のBIGINTの上限値を受理し、成功応答のキャッシュを禁止する。

        Args:
            client: HTTPクライアント。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=DeviceAuthConfig(JWT_SECRET, 300)),
            patch(
                "app.endpoints.device.DeviceController.get_order_history",
                return_value=DeviceOrderHistoryResponse(orders=[]),
            ) as history,
        ):
            response = client.get(PATH.format(visit_id=9223372036854775807), headers=_headers())

        history.assert_called_once_with(
            device_uuid="89100100-0000-4000-8000-000000891001", visit_session_id=9223372036854775807
        )
        assert response.status_code == 200
        assert response.json() == {"orders": []}
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.usefixtures("insert_device_order_history_data")
    def test_with_db_returns_session_order_history(self, client_with_db) -> None:
        """対象セッションの注文と保存済み明細を指定順で返す。

        Args:
            client_with_db: MySQLを使用するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(PATH.format(visit_id=892001), headers=_headers())

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        orders = response.json()["orders"]
        assert [order["menu_order_id"] for order in orders] == [893001, 893003, 893002]
        assert [order["status"] for order in orders] == [1, 3, 5]
        assert orders[0] == {
            "menu_order_id": 893001,
            "created_at": "2026-11-21T03:00:00Z",
            "status": 1,
            "total_amount": "1700.000000",
            "token_symbol": "JPYC",
            "items": [
                {
                    "menu_item_name": "注文時のバーガー",
                    "unit_price": "600.000000",
                    "quantity": 2,
                    "line_amount": "1400.000000",
                    "options": [
                        {
                            "option_group_name": "注文時のトッピング",
                            "option_name": "注文時のソース",
                            "additional_price": "10.000000",
                            "option_quantity": 2,
                        },
                        {
                            "option_group_name": "注文時のトッピング",
                            "option_name": "注文時のチーズ",
                            "additional_price": "80.000000",
                            "option_quantity": 1,
                        },
                    ],
                },
                {
                    "menu_item_name": "注文時のポテト",
                    "unit_price": "300.000000",
                    "quantity": 1,
                    "line_amount": "300.000000",
                    "options": [],
                },
            ],
        }
        assert orders[1]["items"] == []

    @pytest.mark.usefixtures("insert_device_order_history_data")
    def test_with_db_returns_empty_orders_during_checkout(self, client_with_db) -> None:
        """決済処理中のセッションで対象注文が0件の場合に200を返す。

        Args:
            client_with_db: MySQLを使用するHTTPクライアント。

        Returns:
            なし。
        """
        response = client_with_db.get(PATH.format(visit_id=892003), headers=_headers(891002))

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json() == {"orders": []}

    @pytest.mark.usefixtures("insert_device_order_history_data")
    @pytest.mark.parametrize("device_id", [891004, 891005, 891006, 891099])
    def test_with_db_rejects_unavailable_device(self, client_with_db, device_id) -> None:
        """正しい署名のトークンでも利用不可の端末には401を返す。

        Args:
            client_with_db: MySQLを使用するHTTPクライアント。
            device_id: 利用不可の端末ID。

        Returns:
            なし。
        """
        response = client_with_db.get(PATH.format(visit_id=892001), headers=_headers(device_id))

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"]["message"] == DEVICE_AUTHENTICATION_FAILED_ERROR

    @pytest.mark.usefixtures("insert_device_order_history_data")
    @pytest.mark.parametrize("visit_id", [892002, 892004, 892099])
    def test_with_db_rejects_inaccessible_session(self, client_with_db, visit_id) -> None:
        """終了済み、同じ店舗の別端末、または存在しないセッションには404を返す。

        Args:
            client_with_db: MySQLを使用するHTTPクライアント。
            visit_id: 利用できない来店セッションID。

        Returns:
            なし。
        """
        response = client_with_db.get(PATH.format(visit_id=visit_id), headers=_headers())

        assert response.status_code == 404
        assert response.json()["detail"]["message"] == VISIT_SESSION_NOT_FOUND_ERROR
