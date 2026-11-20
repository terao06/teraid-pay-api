"""端末アクセストークン発行APIの入力とHTTP応答を検証する。"""

from unittest.mock import patch

import jwt
import pytest

from app.core.exceptions.message import DEVICE_AUTHENTICATION_FAILED_ERROR
from app.models.mysql.device import Device
from app.models.requests.device_access_token_request import DeviceAccessTokenRequest
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse


TOKEN_PATH = "/device/auth/token"
DEVICE_UUID = "81005100-0000-4000-8000-000000000051"
DEVICE_CREDENTIAL = "test-device-access-credential"
DEVICE_JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"
INVALID_DEVICE_BODY = {
    "detail": {"status": "error", "message": DEVICE_AUTHENTICATION_FAILED_ERROR},
}


class TestIssueDeviceAccessToken:
    """端末アクセストークン発行をHTTP経由で検証する。"""

    @patch("app.middlewares.request_wrapper.TeraidPayApiLog.info")
    @patch("app.endpoints.device.DeviceController.issue_device_access_token")
    def test_returns_token_with_no_store_header(self, mock_issue, mock_log_info, client) -> None:
        """成功時はトークンとキャッシュ制御を返し、関数名だけをログに記録する。"""
        token = DeviceAccessTokenResponse(access_token="test-access-token", expires_in=300)
        mock_issue.return_value = token
        body = {"device_uuid": DEVICE_UUID, "device_credential": DEVICE_CREDENTIAL}

        response = client.post(TOKEN_PATH, json=body)

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }
        mock_issue.assert_called_once_with(request=DeviceAccessTokenRequest(**body))
        mock_log_info.assert_called_once_with("Function: issue_device_access_token")

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"device_credential": DEVICE_CREDENTIAL},
            {"device_uuid": DEVICE_UUID},
            {"device_uuid": "invalid-uuid", "device_credential": DEVICE_CREDENTIAL},
            {"device_uuid": 123, "device_credential": DEVICE_CREDENTIAL},
            {"device_uuid": DEVICE_UUID, "device_credential": ""},
            {"device_uuid": DEVICE_UUID, "device_credential": 123},
            {"device_uuid": DEVICE_UUID, "device_credential": None},
            {"device_uuid": DEVICE_UUID, "device_credential": {"value": DEVICE_CREDENTIAL}},
        ],
    )
    @patch("app.endpoints.device.DeviceController.issue_device_access_token")
    def test_rejects_invalid_body(self, mock_issue, body, client) -> None:
        """不正な入力を422で拒否し、認証情報を応答に含めない。"""
        response = client.post(TOKEN_PATH, json=body)

        assert response.status_code == 422
        assert all(set(error) == {"loc", "type", "msg"} for error in response.json()["detail"])
        assert DEVICE_CREDENTIAL not in response.text
        mock_issue.assert_not_called()

    @pytest.mark.usefixtures("insert_device_access_token_data")
    def test_with_db_issues_token_and_saves_last_authenticated_at(
        self, client_with_db, mysql_session,
    ) -> None:
        """同じ資格情報で再取得でき、署名付きJWTと最終認証日時が確認できる。"""
        payload = {"device_uuid": DEVICE_UUID, "device_credential": DEVICE_CREDENTIAL}

        response = client_with_db.post(TOKEN_PATH, json=payload)
        renewed = client_with_db.post(TOKEN_PATH, json=payload)

        assert response.status_code == renewed.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["token_type"] == "Bearer"
        assert response.json()["expires_in"] == 300
        claims = jwt.decode(
            response.json()["access_token"], DEVICE_JWT_SECRET, algorithms=["HS256"],
        )
        assert claims["sub"] == claims["device_uuid"] == DEVICE_UUID
        assert claims["exp"] - claims["iat"] == 300
        assert response.json()["access_token"] != renewed.json()["access_token"]
        device = mysql_session.get(Device, 810051)
        assert device.last_authenticated_at is not None

    @pytest.mark.usefixtures("insert_device_access_token_data")
    @pytest.mark.parametrize(
        ("device_id", "device_uuid", "device_credential"),
        [
            (810056, "81005600-0000-4000-8000-000000000056", "invalid-credential"),
            (810052, "81005200-0000-4000-8000-000000000052", DEVICE_CREDENTIAL),
            (810053, "81005300-0000-4000-8000-000000000053", DEVICE_CREDENTIAL),
            (810054, "81005400-0000-4000-8000-000000000054", DEVICE_CREDENTIAL),
            (810055, "81005500-0000-4000-8000-000000000055", DEVICE_CREDENTIAL),
            (None, "81005900-0000-4000-8000-000000000059", DEVICE_CREDENTIAL),
        ],
    )
    def test_with_db_rejects_unavailable_device(
        self, client_with_db, mysql_session, device_id, device_uuid, device_credential,
    ) -> None:
        """不正な認証情報や利用不可の端末を同じ401で拒否し、認証日時を更新しない。"""
        response = client_with_db.post(
            TOKEN_PATH, json={"device_uuid": device_uuid, "device_credential": device_credential},
        )

        assert response.status_code == 401
        assert response.json() == INVALID_DEVICE_BODY
        if device_id is not None:
            assert mysql_session.get(Device, device_id).last_authenticated_at is None
