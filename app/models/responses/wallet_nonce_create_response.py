from pydantic import BaseModel


class WalletNonceCreateResponse(BaseModel):
    """ウォレット nonce 作成 API のレスポンスモデルです。"""
    message: str
    nonce: str
    expires_at: str
