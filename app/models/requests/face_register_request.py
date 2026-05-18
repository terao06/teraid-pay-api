from enum import Enum
from pydantic import BaseModel, Field


class ExtensionType(Enum):
    JPEG = "jpeg"
    PNG = "png"

class FaceRegisterRequest(BaseModel):
    user_id: int = Field(..., description="登録対象ユーザーID")
    content: str = Field(..., description="登録対象の顔画像")
    extension_type: ExtensionType = Field(..., description="画像拡張子")
