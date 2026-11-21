"""端末注文の登録、再送照合、履歴取得と会計作成を行う。"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from datetime import timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    DeviceCheckoutConflictException,
    DeviceCheckoutOrderNotFoundException,
    DeviceOrderConflictException,
    DeviceOrderInvalidException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_CHECKOUT_MIXED_TOKEN_ERROR,
    DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR,
    DEVICE_CHECKOUT_PROCESSING_ERROR,
)
from app.models.mysql.menu_checkout import CheckoutScope, MenuCheckout
from app.models.mysql.menu_order import CHECKOUT_UNPAID_STATUSES, MenuOrder, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.models.mysql.visit_session import VisitSessionStatus
from app.models.requests.device_checkout_create_request import DeviceCheckoutCreateRequest, SingleOrderCheckoutRequest
from app.models.requests.device_order_create_request import DeviceOrderCreateRequest
from app.models.responses.device_checkout_create_response import (
    DeviceCheckoutCreateResponse,
    DeviceCheckoutOrderResponse,
)
from app.models.responses.device_order_create_response import DeviceOrderCreateResponse
from app.models.responses.device_order_history_response import (
    DeviceOrderHistoryEntryResponse,
    DeviceOrderHistoryItemResponse,
    DeviceOrderHistoryOptionResponse,
    DeviceOrderHistoryResponse,
)
from app.repositories.mysql.device_order_repository import DeviceOrderRepository
from app.repositories.mysql.device_repository import DeviceRepository
from app.repositories.mysql.visit_session_repository import VisitSessionRepository


_OrderLine = tuple[MenuOrderItem, list[MenuOrderItemOption]]
_MAX_ORDER_AMOUNT = Decimal("99999999999999.999999")
_MYSQL_DUPLICATE_ENTRY = 1062


class DeviceOrderService:
    """端末からの注文を登録し、保存済みの注文を参照して履歴や会計を返す。

    Args:
        なし。

    Returns:
        端末注文サービス。
    """

    def get_order_history(
        self, mysql_session: Session, device_uuid: str, visit_session_id: int
    ) -> DeviceOrderHistoryResponse:
        """端末自身の来店セッションの注文と保存済み明細を階層化して返す。

        Args:
            mysql_session: MySQLセッション。
            device_uuid: 検証済み端末アクセストークンのUUID。
            visit_session_id: 取得対象の来店セッションID。

        Returns:
            新しい順の注文履歴。注文がない場合は空配列を含む。

        Raises:
            UnauthorizedException: 端末が利用できない場合。
            VisitSessionNotFoundException: 端末自身の受付中または決済処理中のセッションがない場合。
        """
        rows = DeviceOrderRepository().get_order_history(mysql_session, device_uuid, visit_session_id)
        if not rows:
            raise UnauthorizedException()
        if rows[0][0] is None:
            raise VisitSessionNotFoundException()

        details = self._group_order_details((order, item, option) for _, order, item, option in rows)
        return DeviceOrderHistoryResponse(
            orders=[
                DeviceOrderHistoryEntryResponse(
                    menu_order_id=order.menu_order_id,
                    created_at=order.created_at.replace(tzinfo=timezone.utc),
                    status=order.status,
                    total_amount=f"{order.total_amount:.6f}",
                    token_symbol=order.token_symbol,
                    items=items,
                )
                for order, items in details.values()
            ]
        )

    def create_checkout(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
        request: DeviceCheckoutCreateRequest,
    ) -> DeviceCheckoutCreateResponse:
        """対象の未払い注文を確定し、確認待ちの会計と保存済み明細を返す。

        Args:
            mysql_session: 参照と登録を同じトランザクションで行うMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            visit_session_id: 会計を作成する来店セッションID。
            request: 一括会計または注文ごとの会計の指定。

        Returns:
            会計ID、対象の注文と明細、合計金額、トークンシンボル。

        Raises:
            UnauthorizedException: 端末が利用できない場合。
            VisitSessionNotFoundException: 端末自身の進行中のセッションが見つからない場合。
            DeviceCheckoutOrderNotFoundException: 個別会計の指定注文が見つからない場合。
            DeviceCheckoutConflictException: 決済処理中、対象が未払いではない、または通貨が混在する場合。
            SQLAlchemyError: DB参照または登録に失敗した場合。
        """
        device = DeviceRepository().get_device_by_uuid_for_update(mysql_session, device_uuid)
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

        visit = VisitSessionRepository().get_visit_session_for_update(
            mysql_session, device.device_id, visit_session_id
        )
        if visit is None or visit.status == VisitSessionStatus.CLOSED:
            raise VisitSessionNotFoundException()
        if visit.status == VisitSessionStatus.CHECKOUT_PROCESSING:
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_PROCESSING_ERROR)

        repository = DeviceOrderRepository()
        menu_order_id = request.menu_order_id if isinstance(request, SingleOrderCheckoutRequest) else None
        rows = repository.get_checkout_orders(mysql_session, device.store_id, visit_session_id, menu_order_id)
        if not rows:
            if menu_order_id is not None:
                raise DeviceCheckoutOrderNotFoundException()
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR)
        if menu_order_id is not None:
            order, _, _ = rows[0]
            if order.paid_at is not None or order.status not in CHECKOUT_UNPAID_STATUSES:
                raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_NO_UNPAID_ORDER_ERROR)

        details = self._group_order_details(rows)
        orders = [order for order, _ in details.values()]
        token_symbol = orders[0].token_symbol
        if any(order.token_symbol != token_symbol for order in orders):
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_MIXED_TOKEN_ERROR)

        total_amount = sum((order.total_amount for order in orders), Decimal("0"))
        checkout_id = repository.create_checkout(
            mysql_session,
            MenuCheckout(
                visit_session_id=visit_session_id,
                scope=CheckoutScope(request.scope),
                total_amount=total_amount,
                token_symbol=token_symbol,
            ),
            orders,
        )
        return DeviceCheckoutCreateResponse(
            checkout_id=checkout_id,
            orders=[
                DeviceCheckoutOrderResponse(
                    menu_order_id=order.menu_order_id,
                    total_amount=f"{order.total_amount:.6f}",
                    items=items,
                )
                for order, items in details.values()
            ],
            total_amount=f"{total_amount:.6f}",
            token_symbol=token_symbol,
        )

    def create_order(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
        idempotency_key: str,
        request: DeviceOrderCreateRequest,
    ) -> tuple[DeviceOrderCreateResponse, bool]:
        """来店セッションに未払いの注文を追加し、既存注文と競合する再送を拒否する。

        Args:
            mysql_session: 新規注文の保存に使用するMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            visit_session_id: 注文を登録する来店セッションID。
            idempotency_key: 注文操作とその再送に共通のキー。
            request: 検証済みのカート明細。

        Returns:
            保存済みの注文情報と、新規登録の場合にTrueとなるフラグ。

        Raises:
            UnauthorizedException: 端末が利用できない場合。
            VisitSessionNotFoundException: 端末自身の受付中セッションが見つからない場合。
            DeviceOrderConflictException: 同じキーで異なる注文が登録されている場合。
            DeviceOrderInvalidException: カートの内容を登録できない場合。
            SQLAlchemyError: DB処理に失敗した場合。
        """
        repository = DeviceOrderRepository()
        context = repository.get_order_context(mysql_session, device_uuid, visit_session_id, idempotency_key)
        if not context:
            raise UnauthorizedException()
        device_id, store_id, active_visit_id, existing_order, _, _ = context[0]
        if active_visit_id is None:
            raise VisitSessionNotFoundException()
        if existing_order is not None:
            return self._replay_order(
                [(existing_order, item, option) for _, _, _, _, item, option in context],
                store_id,
                visit_session_id,
                request,
            ), False

        lines, token_symbol, total_amount = self._price_order(mysql_session, repository, store_id, request)
        device = DeviceRepository().get_device_by_uuid_for_update(mysql_session, device_uuid)
        if (
            device is None
            or device.activated_at is None
            or not device.is_active
            or device.store_id != store_id
            or device.device_id != device_id
        ):
            raise UnauthorizedException()
        if not VisitSessionRepository().has_active_visit_session(
            mysql_session, device_id, visit_session_id, lock_for_update=True
        ):
            raise VisitSessionNotFoundException()

        order = MenuOrder(
            idempotency_key=idempotency_key,
            visit_session_id=visit_session_id,
            store_id=store_id,
            total_amount=total_amount,
            token_symbol=token_symbol,
            status=OrderStatus.PENDING_PAYMENT.value,
        )
        try:
            repository.create_order(mysql_session, order)
        except IntegrityError as error:
            if getattr(error.orig, "args", ())[:1] != (_MYSQL_DUPLICATE_ENTRY,):
                raise
            # MySQLの既定の分離レベルでは、先行するSELECTのスナップショットを破棄する必要がある。
            mysql_session.rollback()
            saved_rows = repository.get_existing_order(mysql_session, idempotency_key, store_id, visit_session_id)
            if not saved_rows:
                raise
            return self._replay_order(saved_rows, store_id, visit_session_id, request), False

        repository.create_order_items(mysql_session, order.menu_order_id, lines)
        return self._to_response(order), True

    @staticmethod
    def _group_order_details(
        rows: Iterable[tuple[MenuOrder | None, MenuOrderItem | None, MenuOrderItemOption | None]],
    ) -> dict[int, tuple[MenuOrder, list[DeviceOrderHistoryItemResponse]]]:
        """結合行を注文IDと商品明細IDでまとめ、明細の順序を保つ。"""
        orders: dict[int, tuple[MenuOrder, list[DeviceOrderHistoryItemResponse]]] = {}
        items: dict[int, DeviceOrderHistoryItemResponse] = {}
        for order, item, option in rows:
            if order is None:
                continue
            if order.menu_order_id not in orders:
                orders[order.menu_order_id] = (order, [])
            if item is None:
                continue
            if item.menu_order_item_id not in items:
                item_response = DeviceOrderHistoryItemResponse(
                    menu_item_name=item.menu_item_name,
                    unit_price=f"{item.unit_price:.6f}",
                    quantity=item.quantity,
                    line_amount=f"{item.line_amount:.6f}",
                    options=[],
                )
                items[item.menu_order_item_id] = item_response
                orders[order.menu_order_id][1].append(item_response)
            if option is not None:
                items[item.menu_order_item_id].options.append(
                    DeviceOrderHistoryOptionResponse(
                        option_group_name=option.option_group_name,
                        option_name=option.option_name,
                        additional_price=f"{option.additional_price:.6f}",
                        option_quantity=option.option_quantity,
                    )
                )
        return orders

    def _price_order(
        self,
        mysql_session: Session,
        repository: DeviceOrderRepository,
        store_id: int,
        request: DeviceOrderCreateRequest,
    ) -> tuple[list[_OrderLine], str, Decimal]:
        """現在の販売情報でカートを検証し、注文時点の明細と合計を作る。"""
        item_ids = {item.menu_item_id for item in request.items}
        option_ids = {option.menu_option_id for item in request.items for option in item.options}
        catalog = repository.get_catalog(mysql_session, store_id, item_ids, option_ids)
        items = {}
        groups_by_item = defaultdict(dict)
        options_by_item = defaultdict(dict)
        for item, group, option in catalog:
            items[item.menu_item_id] = item
            if group is not None:
                groups_by_item[item.menu_item_id][group.menu_option_group_id] = group
            if option is not None:
                options_by_item[item.menu_item_id][option.menu_option_id] = (group, option)

        token_symbols = {item.token_symbol for item in items.values()}
        if items.keys() != item_ids or len(token_symbols) != 1:
            raise DeviceOrderInvalidException()

        lines = []
        total_amount = Decimal(0)
        for display_order, request_item in enumerate(request.items):
            item = items[request_item.menu_item_id]
            options = []
            selections = Counter()
            option_amount = Decimal(0)
            for option_order, requested_option in enumerate(request_item.options):
                available = options_by_item[item.menu_item_id].get(requested_option.menu_option_id)
                if available is None:
                    raise DeviceOrderInvalidException()
                group, option = available
                selections[group.menu_option_group_id] += requested_option.option_quantity
                option_amount += option.additional_price * requested_option.option_quantity
                options.append(
                    MenuOrderItemOption(
                        menu_option_id=option.menu_option_id,
                        option_group_name=group.name,
                        option_name=option.name,
                        additional_price=option.additional_price,
                        option_quantity=requested_option.option_quantity,
                        display_order=option_order,
                    )
                )
            for group in groups_by_item[item.menu_item_id].values():
                if not group.min_selections <= selections[group.menu_option_group_id] <= group.max_selections:
                    raise DeviceOrderInvalidException()

            line_amount = (item.price + option_amount) * request_item.quantity
            total_amount += line_amount
            if abs(line_amount) > _MAX_ORDER_AMOUNT or abs(total_amount) > _MAX_ORDER_AMOUNT:
                raise DeviceOrderInvalidException()
            lines.append((
                MenuOrderItem(
                    menu_item_id=item.menu_item_id,
                    menu_item_name=item.name,
                    unit_price=item.price,
                    quantity=request_item.quantity,
                    line_amount=line_amount,
                    display_order=display_order,
                ),
                options,
            ))
        return lines, token_symbols.pop(), total_amount

    def _replay_order(
        self,
        rows: Sequence[tuple[MenuOrder, MenuOrderItem | None, MenuOrderItemOption | None]],
        store_id: int,
        visit_session_id: int,
        request: DeviceOrderCreateRequest,
    ) -> DeviceOrderCreateResponse:
        """店舗・セッション・明細を照合し、保存済みの注文金額を返す。"""
        order = rows[0][0]
        if order.store_id != store_id or order.visit_session_id != visit_session_id:
            raise DeviceOrderConflictException()

        saved_items = {}
        saved_options = defaultdict(list)
        for _, item, option in rows:
            if item is not None:
                saved_items[item.menu_order_item_id] = (item.menu_item_id, item.quantity)
                if option is not None:
                    saved_options[item.menu_order_item_id].append((option.menu_option_id, option.option_quantity))
        saved_lines = Counter(
            (item_id, quantity, tuple(sorted(saved_options[line_id])))
            for line_id, (item_id, quantity) in saved_items.items()
        )
        requested_lines = Counter(
            (
                item.menu_item_id,
                item.quantity,
                tuple(sorted((option.menu_option_id, option.option_quantity) for option in item.options)),
            )
            for item in request.items
        )
        if saved_lines != requested_lines:
            raise DeviceOrderConflictException()
        return self._to_response(order)

    @staticmethod
    def _to_response(order: MenuOrder) -> DeviceOrderCreateResponse:
        """店舗で確定した金額を6桁固定の文字列に変換する。"""
        return DeviceOrderCreateResponse(
            menu_order_id=order.menu_order_id,
            total_amount=f"{order.total_amount:.6f}",
            token_symbol=order.token_symbol,
        )
