"""来店セッション終了の業務条件と状態遷移を検証する。"""

from collections.abc import Iterator
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    UnauthorizedException,
    VisitSessionCompletionConflictException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import DEVICE_CHECKOUT_PROCESSING_ERROR, VISIT_SESSION_UNPAID_ORDERS_ERROR
from app.models.mysql.device import Device
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.services.device_service import DeviceService


DEVICE_UUID = "93100100-0000-4000-8000-000000931001"
DEVICE_ID = 931001
STORE_ID = 9301
VISIT_ID = 932001
PREVIOUS_END = datetime(2026, 11, 21, 1, 30)


@pytest.fixture
def completion_repositories() -> Iterator[Mock]:
    """端末、来店セッション、注文のリポジトリを差し替える。

    Args:
        なし。

    Yields:
        リポジトリの呼び出し順序を記録するモック。
    """
    repositories = Mock()
    with (
        patch("app.services.device_service.DeviceRepository", return_value=repositories.devices),
        patch("app.services.device_service.VisitSessionRepository", return_value=repositories.visits),
        patch("app.services.device_service.DeviceOrderRepository", return_value=repositories.orders),
    ):
        repositories.devices.get_device_by_uuid_for_update.return_value = Device(
            device_id=DEVICE_ID, store_id=STORE_ID, activated_at=PREVIOUS_END, is_active=True
        )
        repositories.visits.get_visit_session_for_update.return_value = VisitSession(status=VisitSessionStatus.ACTIVE)
        repositories.orders.has_unpaid_orders.return_value = False
        yield repositories


class TestCompleteVisitSession:
    """来店セッションを終了できる条件と再送時の挙動を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_closes_active_visit_after_checking_unpaid_orders(self, completion_repositories: Mock) -> None:
        """端末とセッションを順にロックし、注文を確認して終了時刻を設定する。

        Args:
            completion_repositories: リポジトリの呼び出しを記録するモック。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        visit = completion_repositories.visits.get_visit_session_for_update.return_value
        DeviceService().complete_visit_session(session, DEVICE_UUID, VISIT_ID)

        assert [entry[0] for entry in completion_repositories.mock_calls] == [
            "devices.get_device_by_uuid_for_update", "visits.get_visit_session_for_update", "orders.has_unpaid_orders"
        ]
        completion_repositories.devices.get_device_by_uuid_for_update.assert_called_once_with(session, DEVICE_UUID)
        completion_repositories.visits.get_visit_session_for_update.assert_called_once_with(session, DEVICE_ID, VISIT_ID)
        completion_repositories.orders.has_unpaid_orders.assert_called_once_with(session, STORE_ID, VISIT_ID)
        assert visit.status == VisitSessionStatus.CLOSED
        assert isinstance(visit.ended_at, datetime)

    def test_preserves_ended_at_on_replay(self, completion_repositories: Mock) -> None:
        """終了済みの対象は注文の検索を省き、保持している終了時刻を返却後も維持する。

        Args:
            completion_repositories: リポジトリの呼び出しを記録するモック。

        Returns:
            なし。
        """
        visit = VisitSession(status=VisitSessionStatus.CLOSED, ended_at=PREVIOUS_END)
        completion_repositories.visits.get_visit_session_for_update.return_value = visit

        DeviceService().complete_visit_session(Mock(spec=Session), DEVICE_UUID, VISIT_ID)

        completion_repositories.orders.has_unpaid_orders.assert_not_called()
        assert visit.status == VisitSessionStatus.CLOSED
        assert visit.ended_at == PREVIOUS_END

    @pytest.mark.parametrize(
        ("visit_status", "has_unpaid_orders", "expected_error"),
        [
            (VisitSessionStatus.CHECKOUT_PROCESSING, False, DEVICE_CHECKOUT_PROCESSING_ERROR),
            (VisitSessionStatus.ACTIVE, True, VISIT_SESSION_UNPAID_ORDERS_ERROR),
        ],
    )
    def test_rejects_payment_conflicts(
        self, completion_repositories: Mock, visit_status: VisitSessionStatus, has_unpaid_orders: bool,
        expected_error: str,
    ) -> None:
        """決済処理中または未払いがあると、セッションの状態と終了時刻を維持する。

        Args:
            completion_repositories: リポジトリの呼び出しを記録するモック。
            visit_status: 終了前のセッション状態。
            has_unpaid_orders: 未払い注文の検索結果。
            expected_error: 競合理由の期待値。

        Returns:
            なし。
        """
        visit = VisitSession(status=visit_status)
        completion_repositories.visits.get_visit_session_for_update.return_value = visit
        completion_repositories.orders.has_unpaid_orders.return_value = has_unpaid_orders

        with pytest.raises(VisitSessionCompletionConflictException) as failure:
            DeviceService().complete_visit_session(Mock(spec=Session), DEVICE_UUID, VISIT_ID)

        assert str(failure.value) == expected_error
        assert visit.status == visit_status
        assert visit.ended_at is None
        assert completion_repositories.orders.has_unpaid_orders.call_count == int(has_unpaid_orders)

    @pytest.mark.parametrize(
        "device", [None, Device(is_active=True), Device(activated_at=PREVIOUS_END, is_active=False)]
    )
    def test_rejects_unavailable_device(self, completion_repositories: Mock, device: Device | None) -> None:
        """未登録・未有効化・停止中の端末ではセッションを検索せずに拒否する。

        Args:
            completion_repositories: リポジトリの呼び出しを記録するモック。
            device: 端末の検索結果。

        Returns:
            なし。
        """
        completion_repositories.devices.get_device_by_uuid_for_update.return_value = device

        with pytest.raises(UnauthorizedException):
            DeviceService().complete_visit_session(Mock(spec=Session), DEVICE_UUID, VISIT_ID)

        completion_repositories.visits.get_visit_session_for_update.assert_not_called()

    def test_rejects_missing_visit(self, completion_repositories: Mock) -> None:
        """端末にひもづく対象がなければ注文を検索せずに拒否する。

        Args:
            completion_repositories: リポジトリの呼び出しを記録するモック。

        Returns:
            なし。
        """
        completion_repositories.visits.get_visit_session_for_update.return_value = None

        with pytest.raises(VisitSessionNotFoundException):
            DeviceService().complete_visit_session(Mock(spec=Session), DEVICE_UUID, VISIT_ID)

        completion_repositories.orders.has_unpaid_orders.assert_not_called()
