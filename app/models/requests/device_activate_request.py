"""端末初回有効化APIのリクエストモデルを提供する。"""

from pydantic import BaseModel, Field

from app.core.utils.device_activation import ACTIVATION_CODE_PATTERN


class DeviceActivateRequest(BaseModel):
    """端末初回有効化APIで受け取る有効化コードを検証する。

    Args:
        activation_code: 事前に発行された、ハイフン区切りの有効化コード。

    Returns:
        検証済みの有効化コードを保持するリクエストモデル。

    Raises:
        ValidationError: コードが文字列でない、または発行時の形式と一致しない場合。
    """

    activation_code: str = Field(
        strict=True,
        pattern=ACTIVATION_CODE_PATTERN,
        repr=False,
        description="有効化コード",
    )
