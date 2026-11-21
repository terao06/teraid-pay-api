"""オーダー一覧のレスポンスモデルを提供する。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.mysql.menu_order import OrderStatus


class OrderListOptionResponse(BaseModel):
    """調理時に確認するオプションを表す。

    Args:
        option_group_name: 注文時のオプショングループ名。
        option_name: 注文時のオプション名。
        option_quantity: 商品1個当たりの数量。

    Returns:
        注文されたオプション。
    """

    option_group_name: str
    option_name: str
    option_quantity: int


class OrderListItemResponse(BaseModel):
    """調理する商品と選択されたオプションを表す。

    Args:
        menu_item_name: 注文時の商品名。
        quantity: 商品の注文数量。
        options: 商品1個当たりのオプション一覧。

    Returns:
        注文された商品の明細。
    """

    menu_item_name: str
    quantity: int
    options: list[OrderListOptionResponse]


class OrderListEntryResponse(BaseModel):
    """店舗スタッフが提供する1件の注文を表す。

    Args:
        menu_order_id: 注文 ID。
        visit_session_id: 注文元の来店セッション ID。
        device_name: 注文元の端末名。端末を特定できない場合は None。
        status: オーダー状態の整数コード。
        created_at: 注文受付日時。
        served_at: 提供完了日時。未提供の場合は None。
        items: 注文された商品の一覧。

    Returns:
        注文元と明細を含む注文データ。
    """

    menu_order_id: int
    visit_session_id: int | None
    device_name: str | None
    status: OrderStatus
    created_at: datetime
    served_at: datetime | None
    items: list[OrderListItemResponse]


class OrderListPaginationResponse(BaseModel):
    """オーダー一覧のページ情報を表す。

    Args:
        page: 取得対象のページ番号。
        page_size: 1ページ当たりの最大注文数。
        total: オーダーの総件数。
        total_pages: 総ページ数。

    Returns:
        一覧のページ情報。
    """

    page: int
    page_size: int
    total: int
    total_pages: int


class OrderListResponse(BaseModel):
    """オーダー一覧とページ情報を返す。

    Args:
        orders: 表示対象の注文一覧。
        pagination: 一覧のページ情報。

    Returns:
        オーダー一覧のレスポンス。
    """

    orders: list[OrderListEntryResponse]
    pagination: OrderListPaginationResponse


class OrderListApiResponse(BaseModel):
    """オーダー一覧を店舗管理 API の共通の形式で返す。

    Args:
        status: 処理が成功したことを示す値。
        data: 注文一覧とページ情報。

    Returns:
        オーダー一覧 API の成功レスポンス。
    """

    status: Literal["success"]
    data: OrderListResponse
