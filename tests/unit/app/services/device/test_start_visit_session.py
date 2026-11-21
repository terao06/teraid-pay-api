"""来店セッション開始サービスの端末確認と状態分岐を検証する。"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import UnauthorizedException, VisitSessionConflictException
from app.models.mysql.device import Device
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.services.device_service import DeviceService


DEVICE_UUID = "81006100-0000-4000-8000-000000000061"
DEVICE_ID = 810061
REQUEST_ID = "start-request"
ACTIVE_DEVICE = Device(device_id=DEVICE_ID, activated_at=datetime(2026, 1, 1), is_active=True)


class TestStartVisitSession:
    """認証済み端末の来店セッション開始条件を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_creates_session_when_no_session_is_in_progress(self, device_repository, visit_repository) -> None:
        """端末をロックし、競合がなければ注文受付中のセッションを組み立てて登録する。

        Args:
            device_repository: 端末リポジトリのモック。
            visit_repository: 来店セッションリポジトリのモック。

        Returns:
            なし。
        """
        mysql_session = Mock()
        device_repository.return_value.get_device_by_uuid_for_update.return_value = ACTIVE_DEVICE
        repository = visit_repository.return_value
        repository.get_by_start_request_id.return_value = None
        repository.has_in_progress_session.return_value = False
        repository.create_visit_session.return_value = VisitSession(visit_session_id=123)

        assert DeviceService().start_visit_session(mysql_session, DEVICE_UUID, REQUEST_ID) == (123, True)

        device_repository.return_value.get_device_by_uuid_for_update.assert_called_once_with(
            mysql_session=mysql_session, device_uuid=DEVICE_UUID,
        )
        repository.get_by_start_request_id.assert_called_once_with(
            mysql_session=mysql_session, device_id=DEVICE_ID, start_request_id=REQUEST_ID,
        )
        repository.has_in_progress_session.assert_called_once_with(
            mysql_session=mysql_session, device_id=DEVICE_ID,
        )
        repository.create_visit_session.assert_called_once()
        create_kwargs = repository.create_visit_session.call_args.kwargs
        assert create_kwargs["mysql_session"] is mysql_session
        visit_session = create_kwargs["visit_session"]
        assert isinstance(visit_session, VisitSession)
        assert visit_session.device_id == DEVICE_ID
        assert visit_session.start_request_id == REQUEST_ID
        assert visit_session.status == VisitSessionStatus.ACTIVE

    @pytest.mark.parametrize("status", [VisitSessionStatus.ACTIVE, VisitSessionStatus.CHECKOUT_PROCESSING])
    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_reuses_session_for_same_request(self, device_repository, visit_repository, status) -> None:
        """同じ開始要求が進行中なら、登録せずに既存IDを返す。

        Args:
            device_repository: 端末リポジトリのモック。
            visit_repository: 来店セッションリポジトリのモック。
            status: 既存セッションの状態。

        Returns:
            なし。
        """
        device_repository.return_value.get_device_by_uuid_for_update.return_value = ACTIVE_DEVICE
        repository = visit_repository.return_value
        repository.get_by_start_request_id.return_value = VisitSession(visit_session_id=123, status=status)

        assert DeviceService().start_visit_session(Mock(), DEVICE_UUID, REQUEST_ID) == (123, False)
        repository.create_visit_session.assert_not_called()

    @pytest.mark.parametrize(
        ("existing_session", "has_in_progress"),
        [(VisitSession(status=VisitSessionStatus.CLOSED), False), (None, True)],
    )
    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_rejects_conflicting_session(
        self, device_repository, visit_repository, existing_session, has_in_progress,
    ) -> None:
        """終了済みの開始要求や別の進行中セッションとの競合を拒否する。

        Args:
            device_repository: 端末リポジトリのモック。
            visit_repository: 来店セッションリポジトリのモック。
            existing_session: 同じ開始要求に対応するセッション。
            has_in_progress: 別の進行中セッションが存在するかどうか。

        Returns:
            なし。
        """
        device_repository.return_value.get_device_by_uuid_for_update.return_value = ACTIVE_DEVICE
        repository = visit_repository.return_value
        repository.get_by_start_request_id.return_value = existing_session
        repository.has_in_progress_session.return_value = has_in_progress

        with pytest.raises(VisitSessionConflictException):
            DeviceService().start_visit_session(Mock(), DEVICE_UUID, REQUEST_ID)

        repository.create_visit_session.assert_not_called()

    @pytest.mark.parametrize(
        "device",
        [None, Device(is_active=True), Device(activated_at=datetime(2026, 1, 1), is_active=False)],
    )
    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_rejects_unavailable_device(self, device_repository, visit_repository, device) -> None:
        """利用できない端末の要求ではセッションを検索・登録しない。

        Args:
            device_repository: 端末リポジトリのモック。
            visit_repository: 来店セッションリポジトリのモック。
            device: 未登録・未有効化・停止状態の端末。

        Returns:
            なし。
        """
        device_repository.return_value.get_device_by_uuid_for_update.return_value = device

        with pytest.raises(UnauthorizedException):
            DeviceService().start_visit_session(Mock(), DEVICE_UUID, REQUEST_ID)

        visit_repository.assert_not_called()
