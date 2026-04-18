from pydantic import BaseModel, Field


class StoreWalletResponse(BaseModel):
    """店舗ウォレット情報の API レスポンスモデルです。"""

    store_wallet_id: int = Field(..., description="Store wallet ID")
    store_id: int = Field(..., description="Store ID")
    wallet_address: str = Field(..., description="Wallet address")
    chain_type: str = Field(..., description="Blockchain type")
    network_name: str = Field(..., description="Blockchain network name")
    is_active: bool = Field(..., description="Whether the wallet is active")
    verified_at: str | None = Field(description="Datetime when the wallet was verified")
    created_at: str = Field(..., description="Datetime when the wallet was created")
    updated_at: str = Field(..., description="Datetime when the wallet was last updated")
