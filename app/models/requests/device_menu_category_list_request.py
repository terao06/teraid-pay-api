"""端末用メニューカテゴリー一覧APIのリクエストモデルを提供する。"""

from pydantic import BaseModel, Field, field_validator

from app.core.utils.device_request import SIGNED_BIGINT_MAX, validate_decimal_id


class DeviceMenuCategoryListRequest(BaseModel):
    """端末が指定した来店セッションIDの形式と範囲を検証する。

    Args:
        visit_session_id: 開始APIで発行された来店セッションID。

    Returns:
        検証済みのカテゴリー一覧リクエスト。

    Raises:
        ValidationError: 来店セッションIDが未指定、形式不正、または範囲外の場合。
    """

    visit_session_id: int = Field(
        ge=1,
        le=SIGNED_BIGINT_MAX,
        description="認証済み端末に紐づく来店セッションID。",
    )

    @field_validator("visit_session_id", mode="before")
    @classmethod
    def validate_visit_session_id(cls, value: object) -> str | int:
        """型変換前のクエリ値がASCIIの十進数字で表記されていることを確認する。

        Args:
            value: クエリの文字列、またはモデルに直接渡された整数。

        Returns:
            整数の範囲検証に渡す元の値。

        Raises:
            ValueError: 整数またはASCIIの十進数字だけで構成される文字列以外の場合。
        """
        return validate_decimal_id(value, "来店セッションID")
