"""デバイス更新APIのリクエストモデルを提供する。"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeviceUpdateRequest(BaseModel):
    """デバイス名または利用状態の更新内容を表す。

    Args:
        device_name: 更新後のデバイス名。
        is_active: 更新後の利用可能状態。

    Returns:
        検証済みのデバイス更新リクエスト。
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    device_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Device name",
    )
    is_active: bool | None = Field(default=None, description="Active flag")

    @model_validator(mode="after")
    def validate_update_fields(self):
        """更新項目が指定され、明示的なnullでないことを検証する。

        Args:
            なし。

        Returns:
            検証済みのデバイス更新リクエスト。

        Raises:
            ValueError: 更新項目がない、またはnullが指定された場合。
        """
        if not self.model_fields_set:
            raise ValueError("更新項目を1つ以上指定してください。")
        if "device_name" in self.model_fields_set and self.device_name is None:
            raise ValueError("device_nameにnullは指定できません。")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_activeにnullは指定できません。")
        return self
