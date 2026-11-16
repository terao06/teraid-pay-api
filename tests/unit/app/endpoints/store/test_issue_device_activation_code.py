"""デバイス有効化コード発行Endpointのテスト。"""

import hashlib
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.utils.datetime import JST
from app.models.mysql.device import Device
from app.models.responses.device_activation_code_response import (
    DeviceActivationCodeResponse,
)


class TestIssueDeviceActivationCode:
    """有効化コード発行Endpointのレスポンスと入力検証を確認する。"""

    @patch("app.endpoints.store.StoreController.issue_device_activation_code")
    def test_returns_code_with_no_store_header(
        self,
        mock_issue_code,
        client,
    ) -> None:
        """平文コードを共通レスポンスで返し、キャッシュを禁止する。"""
        mock_issue_code.return_value = DeviceActivationCodeResponse(
            device_id=1,
            activation_code="ABCD-EFGH-JKLM",
            qr_code_image="data:image/png;base64,cG5n",
            activation_expires_at=datetime(2026, 11, 18, 10, 0, tzinfo=JST),
        )

        response = client.post("/store/devices/1/activation-code")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "status": "success",
            "data": {
                "device_id": 1,
                "activation_code": "ABCD-EFGH-JKLM",
                "qr_code_image": "data:image/png;base64,cG5n",
                "activation_expires_at": "2026-11-18T10:00:00+09:00",
            },
        }
        mock_issue_code.assert_called_once_with(store_id=101, device_id=1)

    @pytest.mark.parametrize("device_id", [0, -1, "invalid"])
    def test_returns_validation_error(self, device_id, client) -> None:
        """不正なデバイスIDには422を返す。"""
        response = client.post(f"/store/devices/{device_id}/activation-code")

        assert response.status_code == 422

    def test_requires_store_manager_authentication(
        self,
        client_without_store_manager_auth_override,
    ) -> None:
        """JWTを指定しないリクエストには401を返す。"""
        response = client_without_store_manager_auth_override.post(
            "/store/devices/1/activation-code"
        )

        assert response.status_code == 401

    def test_with_db_reissues_and_invalidates_previous_code(
        self,
        store_client_with_db,
        mysql_session,
    ) -> None:
        """実DBで再発行し、保存ハッシュを最新コードへ置き換える。"""
        create_response = store_client_with_db.post(
            "/store/devices",
            json={"device_name": f"コード発行-{uuid4()}"},
        )
        assert create_response.status_code == 201
        device_id = create_response.json()["data"]["device_id"]

        first_response = store_client_with_db.post(
            f"/store/devices/{device_id}/activation-code"
        )
        second_response = store_client_with_db.post(
            f"/store/devices/{device_id}/activation-code"
        )

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        first_code = first_response.json()["data"]["activation_code"]
        second_code = second_response.json()["data"]["activation_code"]
        assert second_response.json()["data"]["qr_code_image"].startswith(
            "data:image/png;base64,"
        )
        assert first_code != second_code
        assert second_response.headers["cache-control"] == "no-store"

        mysql_session.expire_all()
        device = (
            mysql_session.query(Device)
            .filter(Device.device_id == device_id)
            .one()
        )
        assert device.activation_code_hash == hashlib.sha256(
            second_code.encode("utf-8")
        ).hexdigest()
        assert device.activation_code_hash != hashlib.sha256(
            first_code.encode("utf-8")
        ).hexdigest()
        assert device.activation_expires_at is not None

    def test_with_db_returns_404_for_missing_device(self, store_client_with_db) -> None:
        """対象店舗に存在しないデバイスIDには404を返す。"""
        response = store_client_with_db.post(
            "/store/devices/999999999/activation-code"
        )

        assert response.status_code == 404
