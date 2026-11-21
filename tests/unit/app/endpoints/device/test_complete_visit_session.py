"""来店セッション終了APIのHTTP契約とMySQLへの永続化を検証する。"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    DEVICE_CHECKOUT_PROCESSING_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
    VISIT_SESSION_UNPAID_ORDERS_ERROR,
)
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.responses.visit_session_complete_response import VisitSessionCompleteResponse


PATH = "/device/visit-sessions/{visit_id}/complete"
AUTH = DeviceAuthConfig("test-device-jwt-secret-at-least-32-characters", 300)
DEVICE_ID = 931001
VISIT_ID = 932001


def _headers(device_id: int = DEVICE_ID, config: DeviceAuthConfig = AUTH) -> dict[str, str]:
    """指定端末のテスト用JWTをBearer認証ヘッダーとして返す。"""
    device_uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
    return {"Authorization": f"Bearer {DeviceAuthUtil.create_access_token(device_uuid, config)}"}


class TestCompleteVisitSession:
    """HTTPの入力検証・認証・応答とDBの終了状態を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_returns_closed_visit_with_no_store_header(self, client: TestClient) -> None:
        """ボディなしの要求を受け付け、検証済みの端末UUIDとセッションIDをControllerに渡す。

        Args:
            client: Endpointテスト用クライアント。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=AUTH),
            patch("app.endpoints.device.DeviceController.complete_visit_session") as complete,
        ):
            complete.return_value = VisitSessionCompleteResponse(visit_session_id=VISIT_ID, status="closed")
            response = client.post(PATH.format(visit_id=VISIT_ID), headers=_headers())

        complete.assert_called_once_with(device_uuid="93100100-0000-4000-8000-000000931001", visit_session_id=VISIT_ID)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json() == {"visit_session_id": VISIT_ID, "status": "closed"}

    @pytest.mark.parametrize("visit_id", ["0", "-1", "9223372036854775808", "abc", "1.5", "１２３"])
    def test_rejects_invalid_visit_id_before_mysql(self, client: TestClient, visit_id: str) -> None:
        """形式や範囲が不正なIDにはDBへアクセスせず422を返す。

        Args:
            client: Endpointテスト用クライアント。
            visit_id: 不正なパス入力。

        Returns:
            なし。
        """
        with patch("app.middlewares.transaction.get_mysql_db") as mysql:
            response = client.post(PATH.format(visit_id=visit_id), headers=_headers())

        assert response.status_code == 422
        assert all("input" not in detail for detail in response.json()["detail"])
        mysql.assert_not_called()

    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"Authorization": "Bearer invalid"},
            _headers(config=DeviceAuthConfig(AUTH.jwt_secret, -60)),
        ],
        ids=["missing", "invalid", "expired"],
    )
    def test_rejects_unauthenticated_request_before_mysql(self, client: TestClient, headers: dict[str, str]) -> None:
        """欠落・不正・期限切れのトークンに対してDBへアクセスせず401を返す。

        Args:
            client: Endpointテスト用クライアント。
            headers: 検証対象の認証ヘッダー。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=AUTH),
            patch("app.middlewares.transaction.get_mysql_db") as mysql,
        ):
            response = client.post(PATH.format(visit_id=VISIT_ID), headers=headers)

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["detail"] == {"status": "error", "message": DEVICE_AUTHENTICATION_FAILED_ERROR}
        mysql.assert_not_called()

    def test_reports_auth_config_failure_before_mysql(self, client: TestClient) -> None:
        """認証設定の取得に失敗するとDBへアクセスせず共通形式の500を返す。

        Args:
            client: Endpointテスト用クライアント。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", side_effect=RuntimeError),
            patch("app.middlewares.transaction.get_mysql_db") as mysql,
        ):
            response = client.post(PATH.format(visit_id=VISIT_ID), headers=_headers())

        assert response.status_code == 500
        assert response.json()["detail"] == {"status": "error", "message": SERVER_ERROR}
        mysql.assert_not_called()

    @pytest.mark.usefixtures("insert_visit_session_completion_data")
    def test_with_db_closes_visit_and_preserves_timestamp_on_retry(
        self, client_with_db: TestClient, mysql_session: Session
    ) -> None:
        """未払い注文がないセッションを終了し、再送しても応答と終了時刻が同じことを確認する。

        Args:
            client_with_db: 実DBに接続するEndpointテスト用クライアント。
            mysql_session: DBの更新結果を検証するセッション。

        Returns:
            なし。
        """
        path = PATH.format(visit_id=VISIT_ID)
        response = client_with_db.post(path, headers=_headers())
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json() == {"visit_session_id": VISIT_ID, "status": "closed"}
        visit = mysql_session.get(VisitSession, VISIT_ID)
        assert visit.status == VisitSessionStatus.CLOSED
        ended_at = visit.ended_at
        assert ended_at is not None
        mysql_session.rollback()

        replay = client_with_db.post(path, headers=_headers())
        assert replay.status_code == 200
        assert replay.json() == response.json()
        assert mysql_session.get(VisitSession, VISIT_ID).ended_at == ended_at

    @pytest.mark.usefixtures("insert_visit_session_completion_data")
    def test_with_db_preserves_existing_closed_visit(self, client_with_db: TestClient, mysql_session: Session) -> None:
        """すでに終了している同じ端末のセッションには既存の終了時刻を保持して200を返す。

        Args:
            client_with_db: 実DBに接続するEndpointテスト用クライアント。
            mysql_session: DBの終了時刻を検証するセッション。

        Returns:
            なし。
        """
        visit_id = 932006
        response = client_with_db.post(PATH.format(visit_id=visit_id), headers=_headers())

        assert response.status_code == 200
        assert response.json() == {"visit_session_id": visit_id, "status": "closed"}
        assert mysql_session.get(VisitSession, visit_id).ended_at == datetime(2026, 11, 21, 1, 30)

    @pytest.mark.usefixtures("insert_visit_session_completion_data")
    @pytest.mark.parametrize(
        ("device_id", "visit_id", "status_code", "message", "visit_status"),
        [
            (931002, 932002, 409, VISIT_SESSION_UNPAID_ORDERS_ERROR, VisitSessionStatus.ACTIVE),
            (931003, 932003, 409, DEVICE_CHECKOUT_PROCESSING_ERROR, VisitSessionStatus.CHECKOUT_PROCESSING),
            (931004, 932004, 409, VISIT_SESSION_UNPAID_ORDERS_ERROR, VisitSessionStatus.ACTIVE),
            (931005, 932005, 401, DEVICE_AUTHENTICATION_FAILED_ERROR, VisitSessionStatus.ACTIVE),
            (931001, 932002, 404, VISIT_SESSION_NOT_FOUND_ERROR, VisitSessionStatus.ACTIVE),
            (931001, 932099, 404, VISIT_SESSION_NOT_FOUND_ERROR, None),
        ],
    )
    def test_with_db_rejects_ineligible_targets(
        self, client_with_db: TestClient, mysql_session: Session, device_id: int, visit_id: int, status_code: int,
        message: str, visit_status: VisitSessionStatus | None,
    ) -> None:
        """端末・所属・決済状態が終了条件を満たさない場合に拒否して状態を維持する。

        Args:
            client_with_db: 実DBに接続するEndpointテスト用クライアント。
            mysql_session: DBの状態を検証するセッション。
            device_id: アクセストークンの端末ID。
            visit_id: 終了を試みるセッションID。
            status_code: HTTPステータスの期待値。
            message: 共通エラーメッセージの期待値。
            visit_status: 呼び出し後のDB状態。Noneは対象行なし。

        Returns:
            なし。
        """
        response = client_with_db.post(PATH.format(visit_id=visit_id), headers=_headers(device_id))

        assert response.status_code == status_code
        assert response.json()["detail"] == {"status": "error", "message": message}
        if status_code == 401:
            assert response.headers["WWW-Authenticate"] == "Bearer"
        visit = mysql_session.get(VisitSession, visit_id)
        if visit_status is None:
            assert visit is None
        else:
            assert visit.status == visit_status
            assert visit.ended_at is None
