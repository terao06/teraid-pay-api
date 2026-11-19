"""デバイス一覧取得Endpointのテスト。"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.utils.datetime import JST
from app.models.responses.device_list_response import (
    DeviceListItemResponse,
    DeviceListResponse,
    DevicePaginationResponse,
)


class TestGetDevices:
    """デバイス一覧取得Endpointのレスポンスと入力検証を確認する。"""

    @patch("app.endpoints.store.StoreController.get_devices")
    def test_returns_only_required_device_fields(
        self,
        mock_get_devices,
        client,
    ) -> None:
        """一覧項目を指定された4項目だけ含む共通レスポンスで返す。"""
        mock_get_devices.return_value = DeviceListResponse(
            devices=[
                DeviceListItemResponse(
                    device_id=1,
                    device_name="レジ端末1",
                    is_active=False,
                    created_at=datetime(2026, 11, 16, 10, 0, tzinfo=JST),
                )
            ],
            pagination=DevicePaginationResponse(
                page=2,
                page_size=10,
                total=11,
                total_pages=2,
            ),
        )

        response = client.get(
            "/store/devices",
            params={
                "device_name": "レジ",
                "is_active": "false",
                "page": 2,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data["devices"][0]) == {
            "device_id",
            "device_name",
            "is_active",
            "created_at",
        }
        assert data["pagination"] == {
            "page": 2,
            "page_size": 10,
            "total": 11,
            "total_pages": 2,
        }
        mock_get_devices.assert_called_once_with(
            store_id=101,
            device_name="レジ",
            is_active=False,
            page=2,
            page_size=10,
        )

    @pytest.mark.parametrize(
        "params",
        [
            {"device_name": ""},
            {"page": 0},
            {"page_size": 0},
            {"page_size": 101},
        ],
    )
    def test_returns_validation_error(self, params, client) -> None:
        """不正な検索条件またはページ指定には422を返す。"""
        response = client.get("/store/devices", params=params)

        assert response.status_code == 422

    def test_requires_store_manager_authentication(
        self,
        client_without_store_manager_auth_override,
    ) -> None:
        """JWTを指定しないリクエストには401を返す。"""
        response = client_without_store_manager_auth_override.get("/store/devices")

        assert response.status_code == 401

    @pytest.mark.usefixtures("insert_devices")
    def test_with_db_filters_and_orders_devices(
        self,
        store_client_with_db,
    ) -> None:
        """認証店舗のデバイスを絞り込み、登録日時とIDの降順で返す。"""
        response = store_client_with_db.get(
            "/store/devices",
            params={
                "device_name": "一覧DBテスト",
                "is_active": "false",
                "page": 1,
                "page_size": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["devices"] == [
            {
                "device_id": 810012,
                "device_name": "一覧DBテスト-2",
                "is_active": False,
                "created_at": data["devices"][0]["created_at"],
            }
        ]
        assert data["pagination"] == {
            "page": 1,
            "page_size": 1,
            "total": 2,
            "total_pages": 2,
        }

        second_page = store_client_with_db.get(
            "/store/devices",
            params={"device_name": "一覧DBテスト", "is_active": "false", "page": 2, "page_size": 1},
        )
        assert second_page.status_code == 200
        assert second_page.json()["data"]["devices"][0]["device_id"] == 810011
