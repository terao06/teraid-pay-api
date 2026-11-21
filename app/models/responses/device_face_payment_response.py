"""端末の顔認証決済開始APIの成功レスポンスを定義する。"""

from pydantic import BaseModel

from app.models.mysql.payment_request import PaymentStatus


class DeviceFacePaymentResponse(BaseModel):
    """端末に決済試行のIDと現在の状態を返す。

    Args:
        payment_request_id: 新規または登録済みの決済試行のID。
        status: その試行の現在の状態。

    Returns:
        顔認証決済開始APIのレスポンス。
    """

    payment_request_id: int
    status: PaymentStatus
