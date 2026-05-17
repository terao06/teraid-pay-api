from datetime import datetime

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus


class PaymentRepository:
    """決済情報を取得するレポジトリです。"""

    def get_payment_by_id(
        self,
        mysql_session: Session,
        payment_request_id: int,
        status: PaymentStatus | None = None
    ) -> PaymentRequest | None:
        """決済リクエスト情報を取得します。
        Args:
            mysql_session: SQLAlchemy のセッションです。
            payment_request_id: 絞り込み対象の決済リクエスト ID です。
            status: 絞り込み対象の決済ステータスです。未指定の場合はステータスで絞り込みません。

        Returns:
            PaymentRequest | None: 決済リクエスト情報。対象が存在しない場合は None。
        """
        query = mysql_session.query(
            PaymentRequest
        ).where(
            PaymentRequest.payment_request_id == payment_request_id,
            PaymentRequest.deleted_at.is_(None),
        )
        if status:
            query = query.where(PaymentRequest.status == status.value)
        return query.order_by(PaymentRequest.payment_request_id).first()

    def create_payment_request(self, mysql_session: Session, payment_request: PaymentRequest) -> PaymentRequest:
        """決済リクエスト情報を保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            payment_request: 保存する決済リクエスト情報。

        Returns:
            payment_request: idを付与した決済リクエスト情報
        """
        mysql_session.add(payment_request)
        mysql_session.flush()
        return payment_request
    
    def update_payment_request(self, mysql_session: Session, payment_request: PaymentRequest) -> PaymentRequest:
        now = datetime.now(JST)
        payment_request.updated_at = now
        mysql_session.add(payment_request)
        return payment_request
