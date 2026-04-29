from pydantic import BaseModel, Field


class PaymentCreateResponse(BaseModel):
    """決済情報作成のレスポンスモデルです。"""
    payment_request_id: int = Field(...)
    from_wallet_address: str = Field(..., description="送信元ウォレットアドレス")
    to_wallet_address: str = Field(..., description="送信先ウォレットアドレス")
    amount: int = Field(...)
    token_symbol: str = Field(...)
    chain_id: int = Field(...)
    expires_at: str = Field(...)
