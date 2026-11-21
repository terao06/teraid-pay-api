"""来店セッション開始APIのリクエストモデルを提供する。"""

from pydantic import BaseModel, Field, field_validator


class VisitSessionStartRequest(BaseModel):
    """端末が生成した開始要求IDを検証する。

    Args:
        start_request_id: 開始操作とその再送を識別するID。

    Returns:
        検証済みの来店セッション開始リクエスト。

    Raises:
        ValidationError: 開始要求IDが未指定、または形式が不正な場合。
    """

    start_request_id: str = Field(
        strict=True,
        min_length=1,
        max_length=64,
        description="開始操作とその再送を識別するID。空白のみの値は不可。",
    )

    @field_validator("start_request_id")
    @classmethod
    def validate_start_request_id(cls, value: str) -> str:
        """空白だけの開始要求IDを拒否し、受け取った値を保持する。

        Args:
            value: 型と文字数を検証済みの開始要求ID。

        Returns:
            受け取った開始要求ID。

        Raises:
            ValueError: 値が空白だけの場合。
        """
        if not value.strip():
            raise ValueError("開始要求IDには空白以外の文字が必要です。")
        return value
