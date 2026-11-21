"""来店セッション開始APIのHTTP応答とMySQL上の動作を検証する。"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_CONFLICT_ERROR,
)
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.requests.visit_session_start_request import VisitSessionStartRequest
from app.models.responses.visit_session_start_response import VisitSessionStartResponse


PATH = "/device/visit-sessions"
TOKEN_PATH = "/device/auth/token"
REQUEST_ID = "start-request"
DEVICE_JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"
DEVICE_UUID = "81006100-0000-4000-8000-000000000061"


def _device_headers(device_uuid: str, expires_in: int = 300) -> dict[str, str]:
    """テスト用の端末JWTを署名し、Bearer認証ヘッダーとして返す。"""
    config = DeviceAuthConfig(jwt_secret=DEVICE_JWT_SECRET, access_token_expire_seconds=expires_in)
    token = DeviceAuthUtil.create_access_token(device_uuid, config)
    return {"Authorization": f"Bearer {token}"}


class TestStartVisitSession:
    """来店セッション開始APIの応答と永続化を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("created", "status_code"), [(False, 200), (True, 201)])
    @patch("app.dependencies.device_auth.get_device_auth_config")
    @patch("app.endpoints.device.DeviceController.start_visit_session")
    def test_returns_session_id_with_no_store_header(
        self, mock_start, get_config, created, status_code, client,
    ) -> None:
        """検証済みの端末UUIDをControllerへ渡し、新規・再送ごとに成功応答を返す。

        Args:
            mock_start: Controllerのモック。
            get_config: 端末認証設定のモック。
            created: 新規に作成したかどうか。
            status_code: 期待するHTTPステータス。
            client: テスト用のHTTPクライアント。

        Returns:
            なし。
        """
        get_config.return_value = DeviceAuthConfig(DEVICE_JWT_SECRET, 300)
        request = VisitSessionStartRequest(start_request_id="a" * 64)
        mock_start.return_value = VisitSessionStartResponse(visit_session_id=123), created

        response = client.post(
            PATH, json=request.model_dump(), headers=_device_headers(DEVICE_UUID),
        )

        assert response.status_code == status_code
        assert response.json() == {"visit_session_id": 123}
        assert response.headers["Cache-Control"] == "no-store"
        mock_start.assert_called_once_with(device_uuid=DEVICE_UUID, request=request)

    @pytest.mark.parametrize(
        "body",
        [{}, {"start_request_id": 123}, {"start_request_id": ""}, {"start_request_id": " \t　"}, {"start_request_id": "a" * 65}],
    )
    @patch("app.endpoints.device.DeviceController.start_visit_session")
    def test_rejects_invalid_start_request_id(self, mock_start, body, client) -> None:
        """開始要求IDの入力エラーを値の転載なしで返す。

        Args:
            mock_start: Controllerのモック。
            body: 不正なリクエスト本文。
            client: テスト用のHTTPクライアント。

        Returns:
            なし。
        """
        response = client.post(PATH, json=body)

        assert response.status_code == 422
        [error] = response.json()["detail"]
        assert error["loc"] == ["body", "start_request_id"]
        assert set(error) == {"loc", "type", "msg"}
        mock_start.assert_not_called()

    @pytest.mark.parametrize(
        "headers",
        [{}, {"Authorization": "Basic invalid"}, {"Authorization": "Bearer invalid"}, _device_headers(DEVICE_UUID, expires_in=-60)],
    )
    @patch("app.dependencies.device_auth.get_device_auth_config")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rejects_invalid_bearer_before_database(self, get_mysql_db, get_config, headers, client) -> None:
        """未指定・不正・期限切れの認証情報をDB接続前に拒否する。

        Args:
            get_mysql_db: DB接続のモック。
            get_config: 端末認証設定のモック。
            headers: 認証失敗を引き起こすヘッダー。
            client: テスト用のHTTPクライアント。

        Returns:
            なし。
        """
        get_config.return_value = DeviceAuthConfig(DEVICE_JWT_SECRET, 300)

        response = client.post(PATH, json={"start_request_id": REQUEST_ID}, headers=headers)

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"]["message"] == DEVICE_AUTHENTICATION_FAILED_ERROR
        get_mysql_db.assert_not_called()

    @patch("app.dependencies.device_auth.get_device_auth_config", side_effect=ValueError("invalid configuration"))
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_reports_auth_config_failure(self, get_mysql_db, get_config, client, caplog) -> None:
        """認証設定の読み込み失敗はDB接続前に共通形式の500に変換する。

        Args:
            get_mysql_db: DB接続のモック。
            get_config: 読み込みに失敗する端末認証設定のモック。
            client: テスト用のHTTPクライアント。
            caplog: ログ出力を検証するfixture。

        Returns:
            なし。
        """
        response = client.post(
            PATH, json={"start_request_id": REQUEST_ID}, headers=_device_headers(DEVICE_UUID),
        )

        assert response.status_code == 500
        assert response.json()["detail"] == {"status": "error", "message": SERVER_ERROR}
        get_config.assert_called_once_with()
        get_mysql_db.assert_not_called()
        assert "invalid configuration" not in caplog.text

    @pytest.mark.usefixtures("insert_visit_session_data")
    def test_with_db_creates_and_replays_session_for_authenticated_device(self, client_with_db, mysql_session) -> None:
        """既存の端末認証APIで発行したJWTで開始し、同じ要求の再送でIDを再利用する。

        Args:
            client_with_db: 実DBに接続するHTTPクライアント。
            mysql_session: 作成結果を参照するMySQLセッション。

        Returns:
            なし。
        """
        token_response = client_with_db.post(
            TOKEN_PATH,
            json={"device_uuid": DEVICE_UUID, "device_credential": "test-visit-session-credential"},
        )
        assert token_response.status_code == 200
        headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

        created = client_with_db.post(PATH, json={"start_request_id": REQUEST_ID}, headers=headers)
        assert created.status_code == 201
        replayed = client_with_db.post(PATH, json={"start_request_id": REQUEST_ID}, headers=headers)
        assert replayed.status_code == 200
        assert replayed.json() == created.json()
        assert created.headers["Cache-Control"] == replayed.headers["Cache-Control"] == "no-store"

        conflict = client_with_db.post(PATH, json={"start_request_id": "another-request"}, headers=headers)
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["message"] == VISIT_SESSION_CONFLICT_ERROR

        visit = mysql_session.query(VisitSession).filter_by(device_id=810061).one()
        assert visit.visit_session_id == created.json()["visit_session_id"]
        assert visit.start_request_id == REQUEST_ID
        assert visit.status == VisitSessionStatus.ACTIVE
        assert visit.started_at is not None
        assert visit.ended_at is None

    @pytest.mark.usefixtures("insert_visit_session_data")
    @pytest.mark.parametrize(
        ("device_uuid", "request_id", "status_code"),
        [
            ("81006200-0000-4000-8000-000000000062", "closed-request", 409),
            ("81006500-0000-4000-8000-000000000065", "checkout-request", 200),
            ("81006500-0000-4000-8000-000000000065", "new-request", 409),
        ],
    )
    def test_with_db_respects_existing_session_state(self, client_with_db, device_uuid, request_id, status_code) -> None:
        """終了済みの再送、決済処理中の再送、別要求との競合を区別する。

        Args:
            client_with_db: 実DBに接続するHTTPクライアント。
            device_uuid: 対象の端末UUID。
            request_id: 端末から送る開始要求ID。
            status_code: 期待するHTTPステータス。

        Returns:
            なし。
        """
        response = client_with_db.post(
            PATH, json={"start_request_id": request_id}, headers=_device_headers(device_uuid),
        )

        assert response.status_code == status_code
        if status_code == 200:
            assert response.json() == {"visit_session_id": 820065}
        else:
            assert response.json()["detail"]["message"] == VISIT_SESSION_CONFLICT_ERROR

    @pytest.mark.usefixtures("insert_device_access_token_data")
    @pytest.mark.parametrize(
        "device_uuid",
        [
            "81005200-0000-4000-8000-000000000052",
            "81005300-0000-4000-8000-000000000053",
            "81005400-0000-4000-8000-000000000054",
            "81005900-0000-4000-8000-000000000059",
        ],
    )
    def test_with_db_rejects_unavailable_device(self, client_with_db, device_uuid) -> None:
        """署名が正しくても、停止・削除・未有効化・未登録の端末を拒否する。

        Args:
            client_with_db: 実DBに接続するHTTPクライアント。
            device_uuid: 利用できない端末のUUID。

        Returns:
            なし。
        """
        response = client_with_db.post(
            PATH, json={"start_request_id": REQUEST_ID}, headers=_device_headers(device_uuid),
        )

        assert response.status_code == 401
        assert response.json()["detail"]["message"] == DEVICE_AUTHENTICATION_FAILED_ERROR

    @pytest.mark.usefixtures("insert_visit_session_data")
    @pytest.mark.parametrize(
        ("device_id", "device_uuid", "request_ids", "expected_statuses"),
        [
            (810063, "81006300-0000-4000-8000-000000000063", ("same-request", "same-request"), [200, 201]),
            (810064, "81006400-0000-4000-8000-000000000064", ("first-request", "second-request"), [201, 409]),
        ],
    )
    def test_with_db_serializes_concurrent_starts(
        self, client_with_db, mysql_session, device_id, device_uuid, request_ids, expected_statuses,
    ) -> None:
        """同じ端末に同時に到着した要求で、セッションが1件だけ作成されることを確認する。

        Args:
            client_with_db: 実DBに接続するHTTPクライアント。
            mysql_session: 作成結果を参照するMySQLセッション。
            device_id: テストケース専用の端末ID。
            device_uuid: 認証用JWTに含める端末UUID。
            request_ids: 並行して送信する2件の開始要求ID。
            expected_statuses: ステータスを昇順に並べた期待値。

        Returns:
            なし。
        """
        headers = _device_headers(device_uuid)
        barrier = Barrier(2)

        def send_start(request_id):
            """2件の開始要求を同時に送る。"""
            barrier.wait(timeout=5)
            return client_with_db.post(PATH, json={"start_request_id": request_id}, headers=headers)

        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(send_start, request_id) for request_id in request_ids]
            responses = [request.result(timeout=15) for request in requests]

        assert sorted(response.status_code for response in responses) == expected_statuses
        visit = mysql_session.query(VisitSession).filter_by(device_id=device_id).one()
        assert visit.status == VisitSessionStatus.ACTIVE
        assert all(
            response.json() == {"visit_session_id": visit.visit_session_id}
            for response in responses if response.is_success
        )
