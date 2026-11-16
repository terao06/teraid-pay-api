"""デバイス登録Endpointのテスト。"""

from uuid import UUID
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.device import Device
from app.models.responses.device_create_response import DeviceCreateResponse


class TestCreateDevice:
    """デバイス登録Endpointのレスポンスと入力検証を検証する。"""

    @patch("app.endpoints.store.StoreController.create_device")
    def test_returns_wrapped_created_device(
        self,
        mock_create_device,
        client,
    ) -> None:
        """登録結果を201の共通レスポンス形式で返す。"""
        mock_create_device.return_value = DeviceCreateResponse(
            device_id=1,
        )

        response = client.post(
            "/store/devices",
            json={"device_name": "  レジ端末1  "},
        )

        assert response.status_code == 201
        assert response.json() == {
            "status": "success",
            "data": {
                "device_id": 1,
            },
        }
        assert mock_create_device.call_args.kwargs["store_id"] == 101
        assert mock_create_device.call_args.kwargs["request"].device_name == "レジ端末1"

    @pytest.mark.parametrize(
        "device_name",
        ["", "   ", "a" * 101],
    )
    def test_returns_validation_error(self, device_name, client) -> None:
        """不正なデバイス名に422を返す。"""
        response = client.post(
            "/store/devices",
            json={"device_name": device_name},
        )

        assert response.status_code == 422

    def test_rejects_additional_property(self, client) -> None:
        """未定義のリクエスト項目に422を返す。"""
        response = client.post(
            "/store/devices",
            json={"device_name": "レジ端末1", "store_id": 999},
        )

        assert response.status_code == 422

    def test_requires_store_manager_authentication(
        self,
        client_without_store_manager_auth_override,
    ) -> None:
        """JWTを指定しないリクエストに401を返す。"""
        response = client_without_store_manager_auth_override.post(
            "/store/devices",
            json={"device_name": "レジ端末1"},
        )

        assert response.status_code == 401

    def test_with_db(
        self,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """認証済み管理者の店舗へデバイスを永続化する。"""
        response = store_client_with_db.post(
            "/store/devices",
            json={"device_name": "DBテスト端末"},
        )

        assert response.status_code == 201
        response_data = response.json()["data"]
        device = (
            mysql_session.query(Device)
            .filter(Device.device_id == response_data["device_id"])
            .one()
        )
        assert device.store_id == 101
        assert device.device_name == "DBテスト端末"
        assert str(UUID(device.device_uuid)) == device.device_uuid
        assert len(device.activation_code_hash) == 64
        assert device.is_active is False

