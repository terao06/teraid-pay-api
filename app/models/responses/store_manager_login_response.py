from pydantic import BaseModel, Field


class StoreManagerInfoResponse(BaseModel):
    """ログインした店舗管理者情報。"""

    store_manager_id: int = Field(..., description="Store manager ID")
    store_id: int = Field(..., description="Store ID")
    name: str = Field(..., description="Store manager name")
    roll_id: int = Field(..., description="Role ID")


class StoreManagerLoginResponse(BaseModel):
    """店舗管理者ログイン API のレスポンスモデル。"""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    store_manager: StoreManagerInfoResponse
