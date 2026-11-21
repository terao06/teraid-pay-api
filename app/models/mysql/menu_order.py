"""注文と注文時点の明細を保存する MySQL モデルを提供する。"""

from enum import Enum, IntEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER, TINYINT

from .base_model import Base


class OrderStatus(IntEnum):
    """DB と API が共有するオーダー状態の固定コードを定義する。

    Args:
        value: オーダー状態の整数コード。

    Returns:
        コードに対応するオーダー状態。
    """

    PENDING_PAYMENT = 1
    PAYMENT_PROCESSING = 2
    PAID = 3
    PAYMENT_FAILED = 4
    CANCELED = 5


class OrderFulfillmentStatus(str, Enum):
    """オーダー一覧で指定する提供状態を定義する。

    Args:
        value: 未提供または提供済みを表すクエリの値。

    Returns:
        クエリの値に対応する提供状態。
    """

    UNSERVED = "unserved"
    SERVED = "served"


class MenuOrder(Base):
    """店舗で受け付けた注文と決済・提供の時刻を保持する。

    Args:
        kwargs: 店舗、来店セッション、金額、決済状態などの列の初期値。

    Returns:
        注文を表す ORM インスタンス。
    """

    __tablename__ = "menu_orders"
    __table_args__ = (
        CheckConstraint("status IN (1, 2, 3, 4, 5)", name="ck_menu_orders_status"),
        Index("ix_menu_orders_fulfillment", "store_id", "deleted_at", "served_at", "created_at", "menu_order_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    menu_order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(64, collation="utf8mb4_0900_bin"), nullable=False, unique=True)
    visit_session_id = Column(BigInteger, ForeignKey("visit_sessions.visit_session_id"))
    store_id = Column(BigInteger, ForeignKey("stores.store_id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    total_amount = Column(DECIMAL(20, 6), nullable=False)
    token_symbol = Column(String(20), nullable=False, server_default="JPYC")
    status = Column(
        TINYINT(unsigned=True),
        nullable=False,
        server_default=str(OrderStatus.PENDING_PAYMENT.value),
    )
    paid_at = Column(DateTime)
    served_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=text("(UTC_TIMESTAMP())"))
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("(UTC_TIMESTAMP())"),
        onupdate=func.utc_timestamp(),
    )
    deleted_at = Column(DateTime)


class MenuOrderItem(Base):
    """注文時の商品名、単価、数量を保持する。

    Args:
        kwargs: 注文 ID、商品 ID、商品名、単価、数量、明細金額などの列の初期値。

    Returns:
        注文明細を表す ORM インスタンス。
    """

    __tablename__ = "menu_order_items"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    menu_order_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    menu_order_id = Column(BigInteger, ForeignKey("menu_orders.menu_order_id"), nullable=False)
    menu_item_id = Column(BigInteger, ForeignKey("menu_items.menu_item_id"), nullable=False)
    menu_item_name = Column(String(255), nullable=False)
    unit_price = Column(DECIMAL(20, 6), nullable=False)
    quantity = Column(INTEGER(unsigned=True), nullable=False)
    line_amount = Column(DECIMAL(20, 6), nullable=False)
    display_order = Column(INTEGER(unsigned=True), nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=text("(UTC_TIMESTAMP())"))


class MenuOrderItemOption(Base):
    """注文時のオプション名、追加単価、商品1個当たりの数量を保持する。

    Args:
        kwargs: 注文明細 ID、オプション ID、名称、追加単価などの列の初期値。

    Returns:
        注文オプション明細を表す ORM インスタンス。
    """

    __tablename__ = "menu_order_item_options"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    menu_order_item_option_id = Column(BigInteger, primary_key=True, autoincrement=True)
    menu_order_item_id = Column(BigInteger, ForeignKey("menu_order_items.menu_order_item_id"), nullable=False)
    menu_option_id = Column(BigInteger, ForeignKey("menu_options.menu_option_id"), nullable=False)
    option_group_name = Column(String(100), nullable=False)
    option_name = Column(String(100), nullable=False)
    additional_price = Column(DECIMAL(20, 6), nullable=False, server_default="0")
    option_quantity = Column(INTEGER(unsigned=True), nullable=False, server_default="1")
    display_order = Column(INTEGER(unsigned=True), nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=text("(UTC_TIMESTAMP())"))
