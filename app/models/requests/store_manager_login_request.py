from pydantic import BaseModel, Field


class StoreManagerLoginRequest(BaseModel):
    """店舗管理者ログイン API のリクエストモデル。"""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
