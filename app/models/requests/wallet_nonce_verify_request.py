from pydantic import BaseModel, Field


class WalletVerifyRequest(BaseModel):
    wallet_address: str = Field(..., min_length=42, max_length=42)
    signature: str = Field(..., min_length=1)
    chain_type: str = Field(..., min_length=1, max_length=50)
    network_name: str = Field(..., min_length=1, max_length=50)
    token_symbol: str = Field(..., min_length=1, max_length=20)
    chain_id: int = Field(..., ge=1)
