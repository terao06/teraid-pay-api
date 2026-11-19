"""デバイス詳細取得Endpointのテスト。"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.utils.datetime import JST
from app.models.responses.device_detail_response import DeviceDetailResponse


class TestGetDeviceDetail:
    """デバイス詳細取得Endpointのレスポンスと入力検証を確認する。"""

    @patch("app.endpoints.store.StoreController.get_device_detail")
    def test_returns_only_displayable_fields(
        self,
        mock_get_device_detail,
        client,
    ) -> None:
        """詳細情報を許可された7項目だけ含む共通レスポンスで返す。"""
        mock_get_device_detail.return_value = DeviceDetailResponse(
            device_id=1,
            device_name="レジ端末1",
            is_active=False,
            activated_at=None,
            last_authenticated_at=None,
            created_at=datetime(2026, 11, 16, 10, 0, tzinfo=JST),
            updated_at=datetime(2026, 11, 16, 10, 0, tzinfo=JST),
        )

        response = client.get("/store/devices/1")

        assert response.status_code == 200
        assert set(response.json()["data"]) == {
            "device_id",
            "device_name",
            "is_active",
            "activated_at",
            "last_authenticated_at",
            "created_at",
            "updated_at",
        }
        mock_get_device_detail.assert_called_once_with(store_id=101, device_id=1)

    @pytest.mark.parametrize("device_id", [0, -1, "invalid"])
    def test_returns_validation_error(self, device_id, client) -> None:
        """不正なデバイスIDには422を返す。"""
        response = client.get(f"/store/devices/{device_id}")

        assert response.status_code == 422

    def test_requires_store_manager_authentication(
        self,
        client_without_store_manager_auth_override,
    ) -> None:
        """JWTを指定しないリクエストには401を返す。"""
        response = client_without_store_manager_auth_override.get("/store/devices/1")

        assert response.status_code == 401

    @pytest.mark.usefixtures("insert_devices")
    def test_with_db_returns_registered_device(self, store_client_with_db) -> None:
        """SQLで投入した認証店舗のデバイス詳細を実DBから取得する。"""
        device_id = 810031
        device_name = "詳細DBテスト"

        response = store_client_with_db.get(f"/store/devices/{device_id}")

        assert response.status_code == 200
        detail = response.json()["data"]
        assert set(detail) == {
            "device_id",
            "device_name",
            "is_active",
            "activated_at",
            "last_authenticated_at",
            "created_at",
            "updated_at",
        }
        assert detail["device_id"] == device_id
        assert detail["device_name"] == device_name
        assert detail["is_active"] is False
        assert detail["activated_at"] is None
        assert detail["last_authenticated_at"] is None

    def test_with_db_returns_404_for_missing_device(self, store_client_with_db) -> None:
        """対象店舗に存在しないデバイスIDには404を返す。"""
        response = store_client_with_db.get("/store/devices/999999999")

        assert response.status_code == 404
