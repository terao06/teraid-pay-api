"""端末初回有効化APIの入力、応答、DB更新を検証する。"""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest

from app.core.exceptions.message import DEVICE_ACTIVATION_CODE_INVALID_ERROR
from app.models.mysql.device import Device
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.responses.device_activate_response import DeviceActivateResponse


ACTIVATION_PATH = "/device/activate"
ACTIVATION_CODE = "ABCD-EFGH-JKLM"
DEVICE_UUID = "81004100-0000-4000-8000-000000000041"
INVALID_CODE_BODY = {
    "detail": {"status": "error", "message": DEVICE_ACTIVATION_CODE_INVALID_ERROR}
}


class TestActivateDevice:
    """端末の初回有効化をHTTP経由で検証する。"""

    @patch("app.middlewares.request_wrapper.TeraidPayApiLog.info")
    @patch("app.endpoints.device.DeviceController.activate_device")
    def test_returns_credentials_with_no_store_header(
        self, mock_activate, mock_log_info, client,
    ) -> None:
        """認証情報とキャッシュ制御を返し、リクエストログには関数名だけを記録する。"""
        mock_activate.return_value = DeviceActivateResponse(
            device_uuid=DEVICE_UUID,
            device_credential="test-device-credential",
        )

        response = client.post(ACTIVATION_PATH, json={"activation_code": ACTIVATION_CODE})

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "device_uuid": DEVICE_UUID,
            "device_credential": "test-device-credential",
        }
        mock_activate.assert_called_once_with(
            request=DeviceActivateRequest(activation_code=ACTIVATION_CODE),
        )
        mock_log_info.assert_called_once_with("Function: activate_device")

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"activation_code": None},
            {"activation_code": 1234},
            {"activation_code": "abcd-efgh-jklm"},
            {"activation_code": "ABCD-EFGH-IJKL"},
            {"activation_code": "ABCD-EFGH-JKLM\n"},
            {"activation_code": "ABCDEFGHJKLM"},
        ],
    )
    @patch("app.endpoints.device.DeviceController.activate_device")
    def test_rejects_invalid_body(self, mock_activate, body, client) -> None:
        """不正な入力では値を応答に含めず、業務処理を実行する前に422を返す。"""
        response = client.post(ACTIVATION_PATH, json=body)

        assert response.status_code == 422
        assert all(set(error) == {"loc", "type", "msg"} for error in response.json()["detail"])
        mock_activate.assert_not_called()

    @pytest.mark.usefixtures("insert_device_activation_data")
    def test_with_db_activates_device_and_rejects_replay(self, client_with_db, mysql_session) -> None:
        """有効化状態とハッシュを永続化し、同じコードの再送を拒否する。"""
        payload = {"activation_code": ACTIVATION_CODE}
        response = client_with_db.post(ACTIVATION_PATH, json=payload)
        replay = client_with_db.post(ACTIVATION_PATH, json=payload)

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["device_uuid"] == DEVICE_UUID
        assert replay.status_code == 400
        assert replay.json() == INVALID_CODE_BODY

        device = mysql_session.get(Device, 810041)
        credential = response.json()["device_credential"]
        assert device.device_credential_hash == hashlib.sha256(credential.encode()).hexdigest()
        assert device.is_active is True
        assert device.activated_at is not None
        assert device.activated_at == device.updated_at
        assert device.activation_code_hash is None
        assert device.activation_expires_at is None
        assert device.last_authenticated_at is None

    @pytest.mark.usefixtures("insert_device_activation_data")
    @pytest.mark.parametrize("activation_code", ["NPQR-STUV-WXYZ", "2345-6789-ABCD", "ZZZZ-ZZZZ-ZZZZ"])
    def test_with_db_rejects_unavailable_code(self, client_with_db, activation_code) -> None:
        """期限切れ、削除済み、未発行のコードを同じ400で拒否する。"""
        response = client_with_db.post(ACTIVATION_PATH, json={"activation_code": activation_code})

        assert response.status_code == 400
        assert response.json() == INVALID_CODE_BODY

    @pytest.mark.usefixtures("insert_device_activation_data")
    def test_with_db_consumes_code_once_for_concurrent_requests(self, client_with_db) -> None:
        """同一コードが並行して届いても認証情報を返すリクエストは一つになる。"""
        barrier = Barrier(2)

        def send_activation() -> int:
            """2リクエストを同時に開始し、HTTPステータスを返す。"""
            barrier.wait(timeout=5)
            response = client_with_db.post(ACTIVATION_PATH, json={"activation_code": ACTIVATION_CODE})
            return response.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(send_activation) for _ in range(2)]
            statuses = [request.result(timeout=15) for request in requests]

        assert sorted(statuses) == [200, 400]
