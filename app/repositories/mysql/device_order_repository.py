"""端末の注文登録、履歴取得、会計作成に必要なMySQL操作を提供する。"""

from collections.abc import Sequence

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.mysql.device import Device
from app.models.mysql.menu_checkout import MenuCheckout
from app.models.mysql.menu_checkout_order import MenuCheckoutOrder
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_order import CHECKOUT_UNPAID_STATUSES, MenuOrder
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus


_OrderRow = tuple[MenuOrder, MenuOrderItem | None, MenuOrderItemOption | None]
_ContextRow = tuple[
    int, int, int | None, MenuOrder | None, MenuOrderItem | None, MenuOrderItemOption | None
]
_HistoryRow = tuple[int | None, MenuOrder | None, MenuOrderItem | None, MenuOrderItemOption | None]
_CatalogRow = tuple[MenuItem, MenuOptionGroup | None, MenuOption | None]


def _join_order_details(statement, store_id, visit_session_id):
    """注文の店舗と来店セッションが一致する場合に限り、保存済み明細を結合する。"""
    return (
        statement.outerjoin(
            MenuOrderItem,
            and_(
                MenuOrderItem.menu_order_id == MenuOrder.menu_order_id,
                MenuOrder.store_id == store_id,
                MenuOrder.visit_session_id == visit_session_id,
            ),
        )
        .outerjoin(
            MenuOrderItemOption,
            MenuOrderItemOption.menu_order_item_id == MenuOrderItem.menu_order_item_id,
        )
    )


class DeviceOrderRepository:
    """端末の注文に必要なMySQLクエリを提供する。

    Args:
        なし。

    Returns:
        端末注文リポジトリ。
    """

    def get_order_context(
        self, mysql_session: Session, device_uuid: str, visit_session_id: int, idempotency_key: str
    ) -> Sequence[_ContextRow]:
        """端末、来店セッション、同じキーの注文と明細を1回のSELECTで取得する。

        Args:
            mysql_session: MySQLセッション。
            device_uuid: 認証済みの端末UUID。
            visit_session_id: 注文先の来店セッションID。
            idempotency_key: 全注文で一意となるキー。

        Returns:
            端末ID、店舗ID、有効な来店セッションID、注文、商品明細、オプション明細の結合行。
            端末が利用不可の場合は空。セッションや注文が対象外の場合は該当列がNone。
        """
        statement = (
            select(
                Device.device_id,
                Device.store_id,
                VisitSession.visit_session_id,
                MenuOrder,
                MenuOrderItem,
                MenuOrderItemOption,
            )
            .select_from(Device)
            .outerjoin(
                VisitSession,
                and_(
                    VisitSession.device_id == Device.device_id,
                    VisitSession.visit_session_id == visit_session_id,
                    VisitSession.status == VisitSessionStatus.ACTIVE,
                ),
            )
            .outerjoin(
                MenuOrder,
                and_(
                    VisitSession.visit_session_id.is_not(None),
                    MenuOrder.idempotency_key == idempotency_key,
                ),
            )
            .where(
                Device.device_uuid == device_uuid,
                Device.activated_at.is_not(None),
                Device.is_active.is_(True),
                Device.deleted_at.is_(None),
            )
        )
        statement = _join_order_details(statement, Device.store_id, VisitSession.visit_session_id)
        return mysql_session.execute(statement).tuples().all()

    def get_order_history(
        self, mysql_session: Session, device_uuid: str, visit_session_id: int
    ) -> Sequence[_HistoryRow]:
        """利用可能な端末の来店セッションと注文履歴を1回のSELECTで取得する。

        Args:
            mysql_session: MySQLセッション。
            device_uuid: 検証済み端末アクセストークンのUUID。
            visit_session_id: 取得対象の来店セッションID。

        Returns:
            セッションID、注文、商品明細、オプション明細の結合行。
            利用可能な端末がなければ空。セッションや注文がなければ該当列はNone。

        Raises:
            SQLAlchemyError: DB接続や参照に失敗した場合。
        """
        statement = (
            select(VisitSession.visit_session_id, MenuOrder, MenuOrderItem, MenuOrderItemOption)
            .select_from(Device)
            .outerjoin(
                VisitSession,
                and_(
                    VisitSession.device_id == Device.device_id,
                    VisitSession.visit_session_id == visit_session_id,
                    VisitSession.status.in_((VisitSessionStatus.ACTIVE, VisitSessionStatus.CHECKOUT_PROCESSING)),
                ),
            )
            .outerjoin(
                MenuOrder,
                and_(
                    MenuOrder.store_id == Device.store_id,
                    MenuOrder.visit_session_id == VisitSession.visit_session_id,
                    MenuOrder.deleted_at.is_(None),
                ),
            )
            .where(
                Device.device_uuid == device_uuid,
                Device.activated_at.is_not(None),
                Device.is_active.is_(True),
                Device.deleted_at.is_(None),
            )
            .order_by(
                MenuOrder.created_at.desc(),
                MenuOrder.menu_order_id.desc(),
                MenuOrderItem.display_order,
                MenuOrderItem.menu_order_item_id,
                MenuOrderItemOption.display_order,
                MenuOrderItemOption.menu_order_item_option_id,
            )
        )
        statement = _join_order_details(statement, Device.store_id, VisitSession.visit_session_id)
        return mysql_session.execute(statement).tuples().all()


    def has_unpaid_orders(self, mysql_session: Session, store_id: int, visit_session_id: int) -> bool:
        """指定店舗の来店セッションに未払い注文が残っているかを調べる。

        Args:
            mysql_session: 端末行と来店セッション行を排他ロックしたMySQLセッション。
            store_id: 認証済み端末が所属する店舗のID。
            visit_session_id: 確認対象の来店セッションID。

        Returns:
            削除されていない支払い待ちまたは決済失敗の注文があればTrue。

        Raises:
            SQLAlchemyError: 注文の参照に失敗した場合。
        """
        statement = (
            select(MenuOrder.menu_order_id)
            .where(
                MenuOrder.store_id == store_id,
                MenuOrder.visit_session_id == visit_session_id,
                MenuOrder.deleted_at.is_(None),
                MenuOrder.paid_at.is_(None),
                MenuOrder.status.in_(CHECKOUT_UNPAID_STATUSES),
            )
            .limit(1)
        )
        return mysql_session.scalar(statement) is not None

    def get_checkout_orders(
        self, mysql_session: Session, store_id: int, visit_session_id: int, menu_order_id: int | None
    ) -> Sequence[_OrderRow]:
        """会計候補の注文と保存済み明細を1回のSELECTで取得する。

        Args:
            mysql_session: 対象の端末行とセッション行をロックしたMySQLセッション。
            store_id: 認証済み端末の所属店舗ID。
            visit_session_id: 会計を作成する来店セッションID。
            menu_order_id: 個別会計の注文ID。一括会計の場合はNone。

        Returns:
            一括会計なら未払い注文、個別会計なら指定注文を含む結合行。
            対象注文が存在しない場合は空。

        Raises:
            SQLAlchemyError: DB参照に失敗した場合。
        """
        statement = (
            select(MenuOrder, MenuOrderItem, MenuOrderItemOption)
            .select_from(MenuOrder)
            .where(
                MenuOrder.store_id == store_id,
                MenuOrder.visit_session_id == visit_session_id,
                MenuOrder.deleted_at.is_(None),
            )
            .order_by(
                MenuOrder.created_at.desc(),
                MenuOrder.menu_order_id.desc(),
                MenuOrderItem.display_order,
                MenuOrderItem.menu_order_item_id,
                MenuOrderItemOption.display_order,
                MenuOrderItemOption.menu_order_item_option_id,
            )
        )
        if menu_order_id is None:
            statement = statement.where(
                MenuOrder.paid_at.is_(None), MenuOrder.status.in_(CHECKOUT_UNPAID_STATUSES)
            )
        else:
            statement = statement.where(MenuOrder.menu_order_id == menu_order_id)
        statement = _join_order_details(statement, store_id, visit_session_id)
        return mysql_session.execute(statement).tuples().all()

    def create_checkout(
        self, mysql_session: Session, checkout: MenuCheckout, orders: Sequence[MenuOrder]
    ) -> int:
        """会計と対象注文の金額を同じトランザクションに登録する。

        Args:
            mysql_session: 会計作成中のMySQLセッション。
            checkout: 登録する確認待ちの会計。
            orders: 注文IDごとに1件にまとめた会計対象注文。

        Returns:
            採番済みの会計ID。

        Raises:
            SQLAlchemyError: 会計または対象注文の登録に失敗した場合。
        """
        mysql_session.add(checkout)
        mysql_session.flush()
        mysql_session.add_all(
            [
                MenuCheckoutOrder(
                    checkout_id=checkout.checkout_id,
                    menu_order_id=order.menu_order_id,
                    order_amount=order.total_amount,
                )
                for order in orders
            ]
        )
        mysql_session.flush()
        return checkout.checkout_id

    def get_catalog(
        self, mysql_session: Session, store_id: int, item_ids: set[int], option_ids: set[int]
    ) -> Sequence[_CatalogRow]:
        """対象商品、有効なグループ、選択されたオプションを1回のSELECTで取得する。

        Args:
            mysql_session: MySQLセッション。
            store_id: 認証済み端末が所属する店舗ID。
            item_ids: 注文対象の商品ID。
            option_ids: 注文で選択されたオプションID。

        Returns:
            商品、グループ、オプションの結合行。選択済みオプションがないグループも返す。
        """
        statement = (
            select(MenuItem, MenuOptionGroup, MenuOption)
            .select_from(MenuItem)
            .outerjoin(
                MenuOptionGroup,
                and_(
                    MenuOptionGroup.menu_item_id == MenuItem.menu_item_id,
                    MenuOptionGroup.is_active.is_(True),
                    MenuOptionGroup.deleted_at.is_(None),
                ),
            )
            .outerjoin(
                MenuOption,
                and_(
                    MenuOption.menu_option_group_id == MenuOptionGroup.menu_option_group_id,
                    MenuOption.menu_option_id.in_(option_ids),
                    MenuOption.is_available.is_(True),
                    MenuOption.deleted_at.is_(None),
                ),
            )
            .where(
                MenuItem.store_id == store_id,
                MenuItem.menu_item_id.in_(item_ids),
                MenuItem.is_available.is_(True),
                MenuItem.deleted_at.is_(None),
            )
        )
        return mysql_session.execute(statement).tuples().all()

    def get_existing_order(
        self, mysql_session: Session, idempotency_key: str, store_id: int, visit_session_id: int
    ) -> Sequence[_OrderRow]:
        """並行登録で確定した注文と明細を新しいトランザクションから取得する。

        Args:
            mysql_session: ロールバック後のMySQLセッション。
            idempotency_key: 一意制約に抵触した注文キー。
            store_id: 認証済み端末の所属店舗ID。
            visit_session_id: リクエスト対象の来店セッションID。

        Returns:
            注文と照合対象の保存済み明細。店舗や来店セッションが異なる場合は注文のみ。
        """
        statement = (
            select(MenuOrder, MenuOrderItem, MenuOrderItemOption)
            .select_from(MenuOrder)
            .where(MenuOrder.idempotency_key == idempotency_key)
        )
        statement = _join_order_details(statement, store_id, visit_session_id)
        return mysql_session.execute(statement).tuples().all()

    def create_order(self, mysql_session: Session, order: MenuOrder) -> None:
        """注文ヘッダーを挿入し、主キーを確定する。

        Args:
            mysql_session: 端末と来店セッションをロック済みのMySQLセッション。
            order: 登録対象の注文。

        Returns:
            なし。

        Raises:
            IntegrityError: 冪等性キーの重複などで挿入できない場合。
        """
        mysql_session.add(order)
        mysql_session.flush()

    def create_order_items(
        self,
        mysql_session: Session,
        menu_order_id: int,
        lines: Sequence[tuple[MenuOrderItem, list[MenuOrderItemOption]]],
    ) -> None:
        """商品明細とオプション明細を同じトランザクションに追加する。

        Args:
            mysql_session: 注文ヘッダーの挿入に使用したMySQLセッション。
            menu_order_id: 挿入済みの注文ID。
            lines: 商品明細と、それぞれに属するオプション明細。

        Returns:
            なし。

        Raises:
            SQLAlchemyError: 明細の保存に失敗した場合。
        """
        for item, _ in lines:
            item.menu_order_id = menu_order_id
            mysql_session.add(item)
        mysql_session.flush()

        for item, options in lines:
            for option in options:
                option.menu_order_item_id = item.menu_order_item_id
            mysql_session.add_all(options)
        mysql_session.flush()
