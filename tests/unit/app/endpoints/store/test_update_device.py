"""デバイス更新Endpointのテスト。"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.models.responses.device_update_response import DeviceUpdateResponse


class TestUpdateDevice:
    """デバイス更新Endpointのレスポンスと入力検証を確認する。"""

    @patch("app.endpoints.store.StoreController.update_device")
    def test_returns_updated_device_id(
        self,
        mock_update_device,
        client,
    ) -> None:
        """更新したデバイスIDを共通レスポンス形式で返す。"""
        mock_update_device.return_value = DeviceUpdateResponse(device_id=1)

        response = client.put(
            "/store/devices/1",
            json={"device_name": "  変更後  ", "is_active": False},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {"device_id": 1},
        }
        request = mock_update_device.call_args.kwargs["request"]
        assert request.device_name == "変更後"
        assert request.is_active is False
        mock_update_device.assert_called_once_with(
            store_id=101,
            device_id=1,
            request=request,
        )

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"device_name": ""},
            {"device_name": "   "},
            {"device_name": None},
            {"is_active": None},
            {"unknown": "value"},
        ],
    )
    def test_returns_validation_error_for_invalid_body(self, body, client) -> None:
        """更新項目がない、空、null、または未定義項目の場合は422を返す。"""
        response = client.put("/store/devices/1", json=body)

        assert response.status_code == 422

    @pytest.mark.parametrize("device_id", [0, -1, "invalid"])
    def test_returns_validation_error_for_invalid_id(
        self,
        device_id,
        client,
    ) -> None:
        """不正なデバイスIDには422を返す。"""
        response = client.put(
            f"/store/devices/{device_id}",
            json={"device_name": "変更後"},
        )

        assert response.status_code == 422

    def test_requires_store_manager_authentication(
        self,
        client_without_store_manager_auth_override,
    ) -> None:
        """JWTを指定しないリクエストには401を返す。"""
        response = client_without_store_manager_auth_override.put(
            "/store/devices/1",
            json={"device_name": "変更後"},
        )

        assert response.status_code == 401

    def test_with_db_updates_registered_device(self, store_client_with_db) -> None:
        """実DBに登録したデバイス名と利用状態を更新する。"""
        original_name = f"更新DBテスト-{uuid4()}"
        updated_name = f"更新後-{uuid4()}"
        create_response = store_client_with_db.post(
            "/store/devices",
            json={"device_name": original_name},
        )
        assert create_response.status_code == 201
        device_id = create_response.json()["data"]["device_id"]

        response = store_client_with_db.put(
            f"/store/devices/{device_id}",
            json={"device_name": updated_name, "is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["data"] == {"device_id": device_id}
        detail_response = store_client_with_db.get(f"/store/devices/{device_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["device_name"] == updated_name
        assert detail_response.json()["data"]["is_active"] is False

    def test_with_db_rejects_activating_unactivated_device(
        self,
        store_client_with_db,
    ) -> None:
        """実DBでも未有効化デバイスを直接有効化できない。"""
        create_response = store_client_with_db.post(
            "/store/devices",
            json={"device_name": f"未有効化-{uuid4()}"},
        )
        assert create_response.status_code == 201
        device_id = create_response.json()["data"]["device_id"]

        response = store_client_with_db.put(
            f"/store/devices/{device_id}",
            json={"is_active": True},
        )

        assert response.status_code == 422

    def test_with_db_returns_404_for_missing_device(self, store_client_with_db) -> None:
        """対象店舗に存在しないデバイスIDには404を返す。"""
        response = store_client_with_db.put(
            "/store/devices/999999999",
            json={"device_name": "変更後"},
        )

        assert response.status_code == 404
