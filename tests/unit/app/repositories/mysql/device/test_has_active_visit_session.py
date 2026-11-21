"""来店セッションの所属端末と注文受付中の判定をMySQLで検証する。"""

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.visit_session_repository import VisitSessionRepository


@pytest.mark.usefixtures("insert_visit_session_data")
class TestHasActiveVisitSession:
    """来店セッションID、所属端末、状態による検索範囲を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(
        ("device_id", "visit_session_id", "expected"),
        [
            (810066, 820066, True),
            (810061, 820068, False),
            (810066, 820068, False),
            (810062, 820062, False),
            (810065, 820065, False),
            (810066, 1, False),
        ],
        ids=["active", "same-store-device", "other-store-device", "closed", "checkout", "missing"],
    )
    def test_matches_only_active_session_of_device(
        self, mysql_session: Session, device_id, visit_session_id, expected,
    ) -> None:
        """指定端末に属する注文受付中のセッションだけを対象にする。

        Args:
            mysql_session: テスト用のMySQLセッション。
            device_id: 認証済み端末のID。
            visit_session_id: 照会対象の来店セッションID。
            expected: 注文受付中の対象セッションが見つかるか。

        Returns:
            なし。
        """
        assert VisitSessionRepository().has_active_visit_session(
            mysql_session=mysql_session,
            device_id=device_id,
            visit_session_id=visit_session_id,
        ) is expected
