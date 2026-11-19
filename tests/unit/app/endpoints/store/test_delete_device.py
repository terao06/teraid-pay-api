"""デバイス削除Endpointのテスト。"""

from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.models.responses.device_delete_response import DeviceDeleteResponse


class TestDeleteDevice:
    """削除APIのレスポンス、入力検証、認証を確認する。"""

    @patch("app.endpoints.store.StoreController.delete_device")
    def test_returns_deleted_device_id(self, mock_delete_device, client) -> None:
        """削除したIDを共通レスポンス形式で返す。"""
        mock_delete_device.return_value = DeviceDeleteResponse(device_id=1)

        response = client.delete("/store/devices/1")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": {"device_id": 1}}
        mock_delete_device.assert_called_once_with(store_id=101, device_id=1)

    @pytest.mark.parametrize("device_id", [0, -1, "invalid"])
    def test_rejects_invalid_id(self, device_id, client) -> None:
        """正の整数以外のIDには422を返す。"""
        assert client.delete(f"/store/devices/{device_id}").status_code == 422

    def test_requires_authentication(self, client_without_store_manager_auth_override) -> None:
        """JWTがない場合は401を返す。"""
        response = client_without_store_manager_auth_override.delete(
            "/store/devices/1"
        )
        assert response.status_code == 401

    @pytest.mark.usefixtures("insert_devices")
    def test_with_db_soft_deletes_and_hides_device(
        self, store_client_with_db, mysql_engine
    ) -> None:
        """実DBで論理削除し、詳細取得と再削除で404を返す。"""
        device_id = 810001

        response = store_client_with_db.delete(f"/store/devices/{device_id}")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success", "data": {"device_id": device_id}
        }
        with mysql_engine.connect() as connection:
            deleted_at = connection.execute(
                text("SELECT deleted_at FROM devices WHERE device_id = :device_id"),
                {"device_id": device_id},
            ).scalar_one()
        assert deleted_at is not None
        assert store_client_with_db.get(f"/store/devices/{device_id}").status_code == 404
        assert store_client_with_db.delete(f"/store/devices/{device_id}").status_code == 404

    @pytest.mark.parametrize("device_id", [810002, 810003])
    @pytest.mark.usefixtures("insert_devices")
    def test_with_db_rejects_other_store_or_deleted_device(
        self, store_client_with_db, mysql_engine, device_id
    ) -> None:
        """別店舗または削除済みデバイスには404を返し、行を変更しない。"""
        with mysql_engine.connect() as connection:
            before = connection.execute(
                text("SELECT deleted_at FROM devices WHERE device_id = :device_id"),
                {"device_id": device_id},
            ).scalar_one()

        response = store_client_with_db.delete(f"/store/devices/{device_id}")

        assert response.status_code == 404
        with mysql_engine.connect() as connection:
            after = connection.execute(
                text("SELECT deleted_at FROM devices WHERE device_id = :device_id"),
                {"device_id": device_id},
            ).scalar_one()
        assert after == before
