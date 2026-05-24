from pydantic import BaseModel, Field


class PaymentCreateFromFaceRequest(BaseModel):
    """決済情報作成のリクエストモデルです。"""

    store_id: int = Field(..., ge=1)
    content: str = Field(..., max_length=5000, description="登録対象の顔画像")
    amount: int = Field(..., ge=1)
