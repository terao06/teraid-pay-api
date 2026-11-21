"""店舗別のオーダー一覧を MySQL から取得する。"""

from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.models.mysql.device import Device
from app.models.mysql.menu_order import MenuOrder, OrderFulfillmentStatus, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.models.mysql.visit_session import VisitSession


class StoreOrderRepository:
    """未提供一覧と提供済み履歴の注文および明細を取得する。

    Args:
        なし。

    Returns:
        店舗注文のリポジトリ。
    """

    def get_orders(
        self,
        mysql_session: Session,
        store_id: int,
        fulfillment_status: OrderFulfillmentStatus,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[RowMapping], int]:
        """対象注文を集計し、指定ページ分の注文・端末・明細を一括取得する。

        Args:
            mysql_session: SQLAlchemy の MySQL セッション。
            store_id: 認証済み管理者の所属店舗 ID。
            fulfillment_status: 一覧の提供状態。
            offset: 読み飛ばす注文件数。
            limit: 最大注文件数。

        Returns:
            注文・端末・商品とオプションの結合行、および対象注文の総件数。
        """
        conditions = [MenuOrder.store_id == store_id, MenuOrder.deleted_at.is_(None)]
        if fulfillment_status == OrderFulfillmentStatus.UNSERVED:
            conditions.extend(
                (MenuOrder.served_at.is_(None), MenuOrder.status != OrderStatus.CANCELED.value)
            )
            sort_columns = (MenuOrder.created_at.asc(), MenuOrder.menu_order_id.asc())
        else:
            conditions.append(MenuOrder.served_at.is_not(None))
            sort_columns = (MenuOrder.served_at.desc(), MenuOrder.menu_order_id.desc())

        total = mysql_session.execute(
            select(func.count()).select_from(MenuOrder).where(*conditions)
        ).scalar_one()
        if offset >= total:
            return [], total

        page = (
            select(
                MenuOrder.menu_order_id,
                MenuOrder.visit_session_id,
                MenuOrder.status,
                MenuOrder.created_at,
                MenuOrder.served_at,
            )
            .where(*conditions)
            .order_by(*sort_columns)
            .offset(offset)
            .limit(limit)
            .subquery()
        )
        if fulfillment_status == OrderFulfillmentStatus.UNSERVED:
            page_sort = (page.c.created_at.asc(), page.c.menu_order_id.asc())
        else:
            page_sort = (page.c.served_at.desc(), page.c.menu_order_id.desc())

        query = (
            select(
                page,
                Device.device_name,
                MenuOrderItem.menu_order_item_id,
                MenuOrderItem.menu_item_name,
                MenuOrderItem.quantity,
                MenuOrderItemOption.menu_order_item_option_id,
                MenuOrderItemOption.option_group_name,
                MenuOrderItemOption.option_name,
                MenuOrderItemOption.option_quantity,
            )
            .select_from(page)
            .outerjoin(VisitSession, VisitSession.visit_session_id == page.c.visit_session_id)
            .outerjoin(Device, and_(Device.device_id == VisitSession.device_id, Device.store_id == store_id))
            .outerjoin(MenuOrderItem, MenuOrderItem.menu_order_id == page.c.menu_order_id)
            .outerjoin(MenuOrderItemOption, MenuOrderItemOption.menu_order_item_id == MenuOrderItem.menu_order_item_id)
            .order_by(
                *page_sort,
                MenuOrderItem.display_order,
                MenuOrderItem.menu_order_item_id,
                MenuOrderItemOption.display_order,
                MenuOrderItemOption.menu_order_item_option_id,
            )
        )
        return mysql_session.execute(query).mappings().all(), total
