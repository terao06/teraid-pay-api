from pydantic import BaseModel


class WalletVerifyResponse(BaseModel):
    wallet_address: str
    chain_type: str
    network_name: str
    chain_id: int
    is_active: bool
    verified_at: str
