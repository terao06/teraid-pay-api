"""来店セッションの検索と登録を行うMySQLリポジトリを提供する。"""

from sqlalchemy.orm import Session

from app.models.mysql.visit_session import VisitSession, VisitSessionStatus


class VisitSessionRepository:
    """来店セッションの読み書きを提供する。

    Args:
        なし。

    Returns:
        来店セッションの永続化を扱うリポジトリ。
    """

    def get_by_start_request_id(
        self,
        mysql_session: Session,
        device_id: int,
        start_request_id: str,
    ) -> VisitSession | None:
        """認証済み端末の開始要求に対応するセッションを検索する。

        Args:
            mysql_session: 端末行を排他ロックしたMySQLセッション。
            device_id: 認証済み端末のID。
            start_request_id: 端末が送った開始要求ID。

        Returns:
            開始要求に対応するセッション。見つからない場合はNone。
        """
        return (
            mysql_session.query(VisitSession)
            .filter(
                VisitSession.device_id == device_id,
                VisitSession.start_request_id == start_request_id,
            )
            .one_or_none()
        )

    def has_active_visit_session(
        self,
        mysql_session: Session,
        device_id: int,
        visit_session_id: int,
    ) -> bool:
        """指定されたセッションが端末に属し、注文受付中かを調べる。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_id: 認証済み端末のID。
            visit_session_id: 端末が指定した来店セッションID。

        Returns:
            指定端末に紐づく注文受付中のセッションが見つかればTrue。
        """
        return (
            mysql_session.query(VisitSession.visit_session_id)
            .filter(
                VisitSession.visit_session_id == visit_session_id,
                VisitSession.device_id == device_id,
                VisitSession.status == VisitSessionStatus.ACTIVE,
            )
            .first()
            is not None
        )

    def has_in_progress_session(self, mysql_session: Session, device_id: int) -> bool:
        """端末に注文受付中または決済処理中のセッションがあるか調べる。

        Args:
            mysql_session: 端末行を排他ロックしたMySQLセッション。
            device_id: 認証済み端末のID。

        Returns:
            進行中のセッションがある場合はTrue。
        """
        return (
            mysql_session.query(VisitSession.visit_session_id)
            .filter(
                VisitSession.device_id == device_id,
                VisitSession.status.in_(
                    (VisitSessionStatus.ACTIVE, VisitSessionStatus.CHECKOUT_PROCESSING)
                ),
            )
            .first()
            is not None
        )

    def create_visit_session(
        self,
        mysql_session: Session,
        visit_session: VisitSession,
    ) -> VisitSession:
        """来店セッションをMySQLセッションに追加し、IDを確定する。

        Args:
            mysql_session: 端末行を排他ロックしたMySQLセッション。
            visit_session: 登録対象の来店セッション。

        Returns:
            IDが付与された来店セッション。
        """
        mysql_session.add(visit_session)
        mysql_session.flush()
        return visit_session
