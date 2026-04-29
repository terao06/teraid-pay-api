from pydantic import BaseModel, Field


class PaymentVerifyResponse(BaseModel):
    """決済状況取得APIのレスポンスモデルです。"""
    payment_request_id: int = Field(...)
    status: str = Field(...)
