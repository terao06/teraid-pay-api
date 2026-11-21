"""端末が決済結果確認に使う会計IDと決済試行IDを検証する。"""

from functools import partial
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.core.utils.device_request import SIGNED_BIGINT_MAX, validate_decimal_id
from app.models.requests.device_face_payment_request import DeviceFacePaymentPathRequest


class DevicePaymentResultPathRequest(DeviceFacePaymentPathRequest):
    """正のBIGINTとして会計IDと決済試行IDを受け付ける。

    Args:
        checkout_id: 端末が決済を開始した会計ID。
        payment_request_id: 決済開始APIが返した決済試行ID。

    Returns:
        検証済みのパス入力。

    Raises:
        ValidationError: IDの形式や範囲が不正な場合。
    """

    payment_request_id: Annotated[
        int,
        Field(ge=1, le=SIGNED_BIGINT_MAX),
        BeforeValidator(partial(validate_decimal_id, label="payment_request_id")),
    ]
