from pydantic import BaseModel, Field


class FaceDeleteRequest(BaseModel):
    user_id: int = Field(..., description="登録対象ユーザーID")
