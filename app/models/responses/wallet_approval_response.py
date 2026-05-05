from pydantic import BaseModel, Field


class WalletApprovalResponse(BaseModel):
    wallet_address: str = Field(...)
    chain_id: int = Field(...)
    token_symbol: str = Field(...)
    token_contract_address: str = Field(...)
    spender_address: str = Field(...)
