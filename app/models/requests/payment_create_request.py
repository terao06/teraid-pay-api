from pydantic import BaseModel, Field


class PaymentCreateRequest(BaseModel):
    """決済情報作成のリクエストモデルです。"""

    store_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    amount: int = Field(..., ge=1)
