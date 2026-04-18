from dataclasses import dataclass
from datetime import datetime


@dataclass
class StoreWalletDto:
    """店舗ウォレット情報を受け渡す DTO です。"""

    store_wallet_id: int
    store_id: int
    wallet_address: str
    chain_type: str
    network_name: str
    is_active: bool
    verified_at: datetime
    created_at: datetime
    updated_at: datetime
