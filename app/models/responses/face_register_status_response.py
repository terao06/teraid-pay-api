from pydantic import BaseModel, Field


class FaceRegisterStatusResponse(BaseModel):
    """顔登録状況のレスポンスモデルです。"""
    user_id: int = Field(...)
    is_registered: bool = Field(...)


class FaceRegisterStatusApiResponse(BaseModel):
    status: str = Field(..., description="レスポンスステータス")
    data: FaceRegisterStatusResponse = Field(..., description="顔登録状況")
