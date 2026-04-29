from pydantic import BaseModel, Field


class PaymentTransactionHashRequest(BaseModel):
    """決済情報作成のリクエストモデルです。"""
    transaction_hash: str = Field(...)
