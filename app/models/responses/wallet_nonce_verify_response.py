from pydantic import BaseModel


class StoreWalletVerifyResponse(BaseModel):
    wallet_address: str
    chain_type: str
    network_name: str
    is_primary: bool
    is_active: bool
    verified_at: str
