"""デバイス登録APIのリクエストモデルを提供する。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceCreateRequest(BaseModel):
    """デバイス登録APIのリクエスト。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    device_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Device name",
    )

    @field_validator("device_name")
    @classmethod
    def validate_device_name(cls, value: str) -> str:
        """デバイス名の前後空白を除去し、空文字を拒否する。

        Args:
            value: 入力されたデバイス名。

        Returns:
            前後空白を除去したデバイス名。

        Raises:
            ValueError: 空白除去後のデバイス名が空の場合。
        """
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("デバイス名は必須です。")
        return normalized_value


