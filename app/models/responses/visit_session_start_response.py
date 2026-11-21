"""来店セッション開始APIのレスポンスモデルを提供する。"""

from pydantic import BaseModel, Field


class VisitSessionStartResponse(BaseModel):
    """新規または再送に対応する来店セッションのIDを返す。

    Args:
        visit_session_id: 来店セッションID。

    Returns:
        来店セッション開始APIの成功レスポンス。
    """

    visit_session_id: int = Field(description="来店セッションID")
