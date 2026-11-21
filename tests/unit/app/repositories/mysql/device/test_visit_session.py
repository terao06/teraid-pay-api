"""来店セッションの検索範囲、状態、制約を実DBで検証する。"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.repositories.mysql.device_repository import DeviceRepository
from app.repositories.mysql.visit_session_repository import VisitSessionRepository


@pytest.mark.usefixtures("insert_visit_session_data")
class TestVisitSession:
    """来店セッションの検索条件と永続化を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(
        ("device_id", "request_id", "expected_id"),
        [
            (810062, "closed-request", 820062),
            (810062, "CLOSED-REQUEST", None),
            (810062, "closed-request ", None),
            (810062, "missing-request", None),
            (810062, "start-request", None),
            (810066, "start-request", 820066),
        ],
    )
    def test_matches_request_id_exactly_within_device(
        self, mysql_session: Session, device_id, request_id, expected_id,
    ) -> None:
        """開始要求IDの完全一致と端末の検索範囲を確認する。

        Args:
            mysql_session: テスト用MySQLセッション。
            device_id: 検索対象の端末ID。
            request_id: 開始要求ID。
            expected_id: 一致するセッションID。該当なしの場合はNone。

        Returns:
            なし。
        """
        visit = VisitSessionRepository().get_by_start_request_id(mysql_session, device_id, request_id)

        if expected_id is None:
            assert visit is None
        else:
            assert visit is not None
            assert visit.visit_session_id == expected_id

    @pytest.mark.parametrize(("device_id", "expected"), [(810062, False), (810065, True), (810066, True)])
    def test_detects_only_in_progress_sessions(self, mysql_session: Session, device_id, expected) -> None:
        """注文受付中・決済処理中を進行中とし、終了済みを除外する。

        Args:
            mysql_session: テスト用MySQLセッション。
            device_id: 検索対象の端末ID。
            expected: 進行中のセッションが存在する場合はTrue。

        Returns:
            なし。
        """
        assert VisitSessionRepository().has_in_progress_session(mysql_session, device_id) is expected

    def test_creates_active_session(self, mysql_session: Session) -> None:
        """渡した来店セッションを保存し、自動採番、状態、時刻を確認する。

        Args:
            mysql_session: テスト用MySQLセッション。

        Returns:
            なし。
        """
        device = DeviceRepository().get_device_by_uuid_for_update(
            mysql_session, "81006700-0000-4000-8000-000000000067",
        )
        assert device is not None
        visit_session = VisitSession(
            device_id=device.device_id,
            start_request_id="repository-request",
            status=VisitSessionStatus.ACTIVE,
        )
        visit = VisitSessionRepository().create_visit_session(
            mysql_session=mysql_session, visit_session=visit_session,
        )

        assert visit is visit_session
        assert visit.visit_session_id is not None
        mysql_session.refresh(visit)
        assert visit.device_id == device.device_id
        assert visit.start_request_id == "repository-request"
        assert visit.status == VisitSessionStatus.ACTIVE
        assert visit.started_at is not None
        assert visit.ended_at is None

    def test_rejects_duplicate_request_id_for_same_device(self, mysql_session: Session) -> None:
        """端末と開始要求IDが同じ行の重複をDB制約で拒否する。

        Args:
            mysql_session: テスト用MySQLセッション。

        Returns:
            なし。
        """
        DeviceRepository().get_device_by_uuid_for_update(
            mysql_session, "81006200-0000-4000-8000-000000000062",
        )
        duplicate = VisitSession(device_id=810062, start_request_id="closed-request")
        with pytest.raises(IntegrityError) as exc_info:
            VisitSessionRepository().create_visit_session(mysql_session=mysql_session, visit_session=duplicate)

        assert exc_info.value.orig.args[0] == 1062
