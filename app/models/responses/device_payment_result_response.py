"""端末向け決済結果確認APIの成功レスポンスを定義する。"""

from pydantic import BaseModel

from app.models.mysql.payment_request import PaymentStatus
from app.models.mysql.visit_session import VisitSessionStatus


class DevicePaymentResultResponse(BaseModel):
    """決済結果と、参照時点の来店セッション状態および未払い明細の有無を返す。

    Args:
        payment_request_id: 照会した決済試行ID。
        status: 決済試行の状態。処理中の応答ではconfirmingを返す。
        visit_session_status: 来店セッションの現在の状態。
        has_unpaid_items: 来店セッションに未払い数量が残る明細がある場合はTrue。

    Returns:
        決済結果確認APIの成功レスポンス。
    """

    payment_request_id: int
    status: PaymentStatus
    visit_session_status: VisitSessionStatus
    has_unpaid_items: bool
