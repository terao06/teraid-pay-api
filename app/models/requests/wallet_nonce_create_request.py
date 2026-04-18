from pydantic import BaseModel, Field


class WalletNonceCreateRequest(BaseModel):
    """ウォレット nonce 作成 API のリクエストモデルです。"""

    wallet_address: str = Field(..., min_length=42, max_length=42, description="Wallet address")
    chain_type: str = Field(default="ethereum", max_length=50, description="Blockchain type")
    network_name: str = Field(default="sepolia", max_length=50, description="Blockchain network name")
