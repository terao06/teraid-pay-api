"""来店セッション終了APIの成功レスポンスを提供する。"""

from typing import Literal

from pydantic import BaseModel


class VisitSessionCompleteResponse(BaseModel):
    """終了済みの来店セッションのIDと状態を返す。

    Args:
        visit_session_id: 終了対象の来店セッションID。
        status: 終了済みを表すclosed。

    Returns:
        来店セッション終了APIの成功レスポンス。
    """

    visit_session_id: int
    status: Literal["closed"]
