"""メニューオプション構成更新APIのリクエストモデルを提供する。"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MenuOptionUpdateRequest(BaseModel):
    """更新後のメニューオプションを表す。

    Args:
        menu_option_id: 更新対象のオプションID。新規追加時はNone。
        name: オプション名。
        additional_price: 追加料金。
        display_order: 表示順。
        is_available: 選択可能状態。

    Returns:
        検証済みのメニューオプション更新情報。
    """

    model_config = ConfigDict(extra="forbid")

    menu_option_id: int | None = Field(default=None, ge=1)
    name: str = Field(..., min_length=1, max_length=100)
    additional_price: Decimal = Field(
        ...,
        ge=0,
        max_digits=20,
        decimal_places=6,
    )
    display_order: int = Field(..., ge=0)
    is_available: bool = Field(...)


class MenuOptionGroupUpdateRequest(BaseModel):
    """更新後のメニューオプショングループを表す。

    Args:
        menu_option_group_id: 更新対象のグループID。新規追加時はNone。
        name: グループ名。
        min_selections: 最小選択数。
        max_selections: 最大選択数。
        display_order: 表示順。
        is_active: 有効状態。
        options: 更新後のオプション一覧。

    Returns:
        検証済みのメニューオプショングループ更新情報。
    """

    model_config = ConfigDict(extra="forbid")

    menu_option_group_id: int | None = Field(default=None, ge=1)
    name: str = Field(..., min_length=1, max_length=100)
    min_selections: int = Field(..., ge=0)
    max_selections: int = Field(..., ge=1)
    display_order: int = Field(..., ge=0)
    is_active: bool = Field(...)
    options: list[MenuOptionUpdateRequest] = Field(...)

    @model_validator(mode="after")
    def validate_selection_range(self):
        """最小選択数が最大選択数以下であることを検証する。

        Returns:
            選択数が検証済みのリクエストモデル。

        Raises:
            ValueError: 最小選択数が最大選択数を上回る場合。
        """
        if self.min_selections > self.max_selections:
            raise ValueError(
                "min_selections must be less than or equal to max_selections"
            )
        return self


class MenuOptionGroupsUpdateRequest(BaseModel):
    """メニュー商品の更新後のオプション構成全体を表す。

    Args:
        option_groups: 更新後のオプショングループ一覧。空配列は全削除を表す。

    Returns:
        ID重複を検証済みのオプション構成更新リクエスト。
    """

    model_config = ConfigDict(extra="forbid")

    option_groups: list[MenuOptionGroupUpdateRequest] = Field(...)

    @model_validator(mode="after")
    def validate_unique_ids(self):
        """既存グループIDとオプションIDが重複していないことを検証する。

        Returns:
            ID重複を検証済みのリクエストモデル。

        Raises:
            ValueError: 同じグループIDまたはオプションIDが複数回指定された場合。
        """
        group_ids = [
            group.menu_option_group_id
            for group in self.option_groups
            if group.menu_option_group_id is not None
        ]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("menu_option_group_id must not be duplicated")

        option_ids = [
            option.menu_option_id
            for group in self.option_groups
            for option in group.options
            if option.menu_option_id is not None
        ]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("menu_option_id must not be duplicated")
        return self
