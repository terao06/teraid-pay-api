from pydantic import BaseModel, Field


class PaymentTransactionHashResponse(BaseModel):
    """決済情報作成のレスポンスモデルです。"""
    payment_request_id: int = Field(...)
    transaction_hash: str = Field(...)
