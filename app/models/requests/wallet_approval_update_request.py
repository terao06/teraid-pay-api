from pydantic import BaseModel, Field


class WalletApprovalUpdateRequest(BaseModel):
    """ウォレット approve 状態更新 API のリクエストモデルです。"""

    tx_hash: str = Field(..., min_length=66, max_length=66, description="Approve transaction hash")
