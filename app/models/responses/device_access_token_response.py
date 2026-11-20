"""端末アクセストークン発行APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class DeviceAccessTokenResponse(BaseModel):
    """認証済み端末に発行したアクセストークンを表す。

    Args:
        access_token: 端末用APIで使用するJWTアクセストークン。
        token_type: アクセストークンの種別。
        expires_in: アクセストークンの有効期間（秒）。

    Returns:
        端末アクセストークン発行APIのレスポンスモデル。
    """

    access_token: str = Field(repr=False, description="端末アクセストークン")
    token_type: str = Field(default="Bearer", description="トークン種別")
    expires_in: int = Field(description="有効期間（秒）")
