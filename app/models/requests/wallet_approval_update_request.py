from pydantic import BaseModel, Field


SIGNATURE_HEX_LENGTH = 66
RECOVERY_ID_MIN = 0
RECOVERY_ID_MAX = 255


class WalletApprovalUpdateRequest(BaseModel):
    """ウォレット permit 承認状態更新 API のリクエストモデルです。"""

    allowance_value: int = Field(
        ...,
        gt=0,
        description="permit で PaymentProcessor に許可するトークン最小単位の allowance 値",
    )
    signature_deadline: int = Field(
        ...,
        gt=0,
        description="permit 署名の有効期限を表す Unix タイムスタンプ",
    )
    signature_recovery_id: int = Field(
        ...,
        ge=RECOVERY_ID_MIN,
        le=RECOVERY_ID_MAX,
        description="ウォレットが作成した permit 署名から取り出した署名者復元用ID",
    )
    signature_first_32_bytes: str = Field(
        ...,
        min_length=SIGNATURE_HEX_LENGTH,
        max_length=SIGNATURE_HEX_LENGTH,
        description="ウォレットが作成した permit 署名から取り出した前半32バイト",
    )
    signature_second_32_bytes: str = Field(
        ...,
        min_length=SIGNATURE_HEX_LENGTH,
        max_length=SIGNATURE_HEX_LENGTH,
        description="ウォレットが作成した permit 署名から取り出した後半32バイト",
    )
