"""会計作成で利用する来店セッション検索の排他ロックを検証する。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.repositories.mysql.visit_session_repository import VisitSessionRepository


@pytest.mark.usefixtures("insert_device_checkout_data")
class TestGetVisitSessionForUpdate:
    """端末の所属、状態、行ロックを確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_returns_only_own_session_with_its_current_status(self, mysql_session) -> None:
        """指定端末に属するセッションの現在の状態を取得する。

        Args:
            mysql_session: 初期化済みのテスト用MySQLセッション。

        Returns:
            なし。
        """
        repository = VisitSessionRepository()
        assert repository.get_visit_session_for_update(mysql_session, 901001, 902003) is None
        visit = repository.get_visit_session_for_update(mysql_session, 901002, 902003)
        assert visit.status == VisitSessionStatus.CHECKOUT_PROCESSING

    def test_keeps_row_locked_until_transaction_ends(self, mysql_engine) -> None:
        """ロック中は別接続が取得できず、ロールバック後に取得できる。

        Args:
            mysql_engine: 独立したMySQLセッションを作るEngine。

        Returns:
            なし。
        """
        competing_query = (
            select(VisitSession.visit_session_id)
            .where(VisitSession.visit_session_id == 902001)
            .with_for_update(nowait=True)
        )
        with Session(mysql_engine) as locking_session, Session(mysql_engine) as competing_session:
            visit = VisitSessionRepository().get_visit_session_for_update(locking_session, 901001, 902001)
            assert visit.visit_session_id == 902001
            with pytest.raises(OperationalError) as failure:
                competing_session.scalar(competing_query)
            assert failure.value.orig.args[0] == 3572
            competing_session.rollback()
            locking_session.rollback()
            assert competing_session.scalar(competing_query) == 902001
