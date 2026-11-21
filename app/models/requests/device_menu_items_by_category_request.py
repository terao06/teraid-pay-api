"""端末用カテゴリー別メニュー取得APIのリクエストモデルを提供する。"""

from functools import partial
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.core.utils.device_request import SIGNED_BIGINT_MAX, validate_decimal_id


_PositiveBigint = Annotated[int, Field(ge=1, le=SIGNED_BIGINT_MAX)]


class DeviceMenuItemsByCategoryRequest(BaseModel):
    """カテゴリー別メニュー取得のパスとクエリの入力を検証する。

    Args:
        menu_category_id: パスで指定されたメニューカテゴリーID。
        visit_session_id: クエリで指定された来店セッションID。

    Returns:
        検証済みのカテゴリー別メニュー取得リクエスト。

    Raises:
        ValidationError: 必須IDが未指定、形式不正、または範囲外の場合。
    """

    menu_category_id: Annotated[
        _PositiveBigint,
        BeforeValidator(partial(validate_decimal_id, label="メニューカテゴリーID")),
    ] = Field(description="取得対象のメニューカテゴリーID。")
    visit_session_id: Annotated[
        _PositiveBigint,
        BeforeValidator(partial(validate_decimal_id, label="来店セッションID")),
    ] = Field(description="認証済み端末に紐づく来店セッションID。")
