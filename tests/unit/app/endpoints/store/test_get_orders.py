"""店舗管理者認証付きのオーダー一覧 API を検証する。"""

from unittest.mock import patch

import pytest

from app.models.mysql.menu_order import OrderFulfillmentStatus
from app.models.responses.order_list_response import OrderListPaginationResponse, OrderListResponse


PATH = "/store/orders"


class TestGetOrders:
    """オーダー一覧の認証、入力検証と実 DB の応答を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @patch("app.endpoints.store.StoreController.get_orders")
    def test_uses_auth_store_and_forwards_query(self, mock_get_orders, client) -> None:
        """リクエストの店舗 ID にかかわらず、認証された店舗を使用する。

        Args:
            mock_get_orders: コントローラーのモック。
            client: 管理者認証を上書きしたテストクライアント。

        Returns:
            なし。
        """
        mock_get_orders.return_value = OrderListResponse(
            orders=[], pagination=OrderListPaginationResponse(page=2, page_size=5, total=0, total_pages=0)
        )

        response = client.get(PATH, params={"fulfillment_status": "served", "page": 2, "page_size": 5, "store_id": 112})

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": mock_get_orders.return_value.model_dump()}
        mock_get_orders.assert_called_once_with(
            store_id=101, fulfillment_status=OrderFulfillmentStatus.SERVED, page=2, page_size=5
        )

    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"fulfillment_status": "all"},
            {"fulfillment_status": "unserved", "page": 0},
            {"fulfillment_status": "served", "page": "invalid"},
            {"fulfillment_status": "served", "page_size": 0},
            {"fulfillment_status": "unserved", "page_size": 101},
        ],
    )
    def test_rejects_invalid_query(self, params, client) -> None:
        """提供状態またはページ指定が不正なら HTTP 422 を返す。

        Args:
            params: 不正なクエリ。
            client: 管理者認証を上書きしたテストクライアント。

        Returns:
            なし。
        """
        assert client.get(PATH, params=params).status_code == 422

    def test_requires_store_manager_auth(self, client_without_store_manager_auth_override) -> None:
        """管理者トークンがないリクエストには HTTP 401 を返す。

        Args:
            client_without_store_manager_auth_override: 管理者認証を実行するテストクライアント。

        Returns:
            なし。
        """
        response = client_without_store_manager_auth_override.get(PATH, params={"fulfillment_status": "served"})

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.usefixtures("insert_order_list_data")
    @pytest.mark.parametrize("store_client_with_db", ["unserved-orders-manager@example.com"], indirect=True)
    def test_with_db_unserved_includes_all_items_on_one_order_page(self, store_client_with_db) -> None:
        """店舗に属する未提供の注文を、注文時の明細と一緒に返す。

        Args:
            store_client_with_db: 実 DB と店舗管理者 JWT を使用するテストクライアント。

        Returns:
            なし。
        """
        response = store_client_with_db.get(PATH, params={"fulfillment_status": "unserved", "page_size": 1})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pagination"] == {"page": 1, "page_size": 1, "total": 3, "total_pages": 3}
        assert data["orders"] == [
            {
                "menu_order_id": 870101,
                "visit_session_id": 862001,
                "device_name": "カテゴリー別メニュー取得端末",
                "status": 1,
                "created_at": "2026-11-16T10:00:00+09:00",
                "served_at": None,
                "items": [
                    {
                        "menu_item_name": "特製チーズバーガー",
                        "quantity": 2,
                        "options": [
                            {"option_group_name": "トッピング", "option_name": "追加ベーコン", "option_quantity": 1},
                            {"option_group_name": "トッピング", "option_name": "追加チーズ", "option_quantity": 1},
                        ],
                    },
                    {"menu_item_name": "フライドポテト", "quantity": 1, "options": []},
                ],
            }
        ]

    @pytest.mark.usefixtures("insert_order_list_data")
    @pytest.mark.parametrize("store_client_with_db", ["unserved-orders-manager@example.com"], indirect=True)
    def test_with_db_served_history_includes_unpaid(self, store_client_with_db) -> None:
        """提供済みの注文を提供時刻順に返し、未払いの注文も含める。

        Args:
            store_client_with_db: 実 DB と店舗管理者 JWT を使用するテストクライアント。

        Returns:
            なし。
        """
        response = store_client_with_db.get(PATH, params={"fulfillment_status": "served"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pagination"] == {"page": 1, "page_size": 20, "total": 3, "total_pages": 1}
        assert [order["menu_order_id"] for order in data["orders"]] == [870109, 870108, 870104]
        assert [order["status"] for order in data["orders"]] == [5, 3, 1]
        assert data["orders"][-1]["served_at"] == "2026-11-16T10:30:00+09:00"

    @pytest.mark.usefixtures("insert_order_list_data")
    @pytest.mark.parametrize("store_client_with_db", ["no-wallet-manager@example.com"], indirect=True)
    def test_with_db_returns_empty_for_manager_without_orders(self, store_client_with_db) -> None:
        """注文のない店舗では、他店舗に注文があっても空の一覧を返す。

        Args:
            store_client_with_db: 注文のない店舗に所属する管理者のテストクライアント。

        Returns:
            なし。
        """
        response = store_client_with_db.get(PATH, params={"fulfillment_status": "unserved"})

        assert response.status_code == 200
        assert response.json()["data"] == {
            "orders": [],
            "pagination": {"page": 1, "page_size": 20, "total": 0, "total_pages": 0},
        }
