"""注文と明細の結合結果から管理画面用の一覧を組み立てる。"""

from datetime import timezone

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.models.mysql.menu_order import OrderFulfillmentStatus
from app.models.responses.order_list_response import (
    OrderListEntryResponse,
    OrderListItemResponse,
    OrderListOptionResponse,
    OrderListPaginationResponse,
    OrderListResponse,
)
from app.repositories.mysql.store_order_repository import StoreOrderRepository


class StoreOrderService:
    """店舗のオーダー一覧とページ情報を組み立てる。

    Args:
        なし。

    Returns:
        店舗注文のサービス。
    """

    def get_orders(
        self,
        mysql_session: Session,
        store_id: int,
        fulfillment_status: OrderFulfillmentStatus,
        page: int,
        page_size: int,
    ) -> OrderListResponse:
        """結合行を注文単位にまとめ、注文時の商品名・オプション名とページ情報を返す。

        Args:
            mysql_session: SQLAlchemy の MySQL セッション。
            store_id: 認証済み管理者の所属店舗 ID。
            fulfillment_status: 一覧の提供状態。
            page: 取得するページ番号。
            page_size: 1ページ当たりの最大注文件数。

        Returns:
            指定ページの注文一覧とページ情報。
        """
        rows, total = StoreOrderRepository().get_orders(
            mysql_session=mysql_session,
            store_id=store_id,
            fulfillment_status=fulfillment_status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        orders: dict[int, OrderListEntryResponse] = {}
        items: dict[int, OrderListItemResponse] = {}
        for row in rows:
            order_id = row["menu_order_id"]
            if order_id not in orders:
                served_at = row["served_at"]
                orders[order_id] = OrderListEntryResponse(
                    menu_order_id=order_id,
                    visit_session_id=row["visit_session_id"],
                    device_name=row["device_name"],
                    status=row["status"],
                    created_at=row["created_at"].replace(tzinfo=timezone.utc).astimezone(JST),
                    served_at=served_at.replace(tzinfo=timezone.utc).astimezone(JST) if served_at else None,
                    items=[],
                )
            item_id = row["menu_order_item_id"]
            if item_id is None:
                continue
            if item_id not in items:
                items[item_id] = OrderListItemResponse(
                    menu_item_name=row["menu_item_name"], quantity=row["quantity"], options=[]
                )
                orders[order_id].items.append(items[item_id])
            if row["menu_order_item_option_id"] is not None:
                items[item_id].options.append(
                    OrderListOptionResponse(
                        option_group_name=row["option_group_name"],
                        option_name=row["option_name"],
                        option_quantity=row["option_quantity"],
                    )
                )

        return OrderListResponse(
            orders=list(orders.values()),
            pagination=OrderListPaginationResponse(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=(total + page_size - 1) // page_size,
            ),
        )
