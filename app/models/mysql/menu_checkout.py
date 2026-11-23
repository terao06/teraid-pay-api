"""来店セッションの会計を保存するMySQLモデルを提供する。"""

from enum import Enum

from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, Enum as SQLAlchemyEnum, ForeignKey, Index, String, text

from .base_model import Base


class CheckoutScope(str, Enum):
    """一括会計と移行前の会計で保存された対象範囲を定義する。

    Args:
        value: 一括会計または移行前の個別会計を表す値。

    Returns:
        指定値に対応する会計範囲。
    """

    ALL_UNPAID = "all_unpaid"
    SINGLE_ORDER = "single_order"


class CheckoutStatus(str, Enum):
    """会計の状態を定義する。

    Args:
        value: 会計の状態を表す値。

    Returns:
        指定値に対応する会計状態。
    """

    PENDING_CONFIRMATION = "pending_confirmation"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"


class MenuCheckout(Base):
    """来店セッションの会計範囲と合計金額を保存する。

    Args:
        kwargs: 来店セッションID、会計範囲、合計金額などの列の初期値。

    Returns:
        来店セッションの会計を表すORMモデル。
    """

    __tablename__ = "menu_checkouts"
    __table_args__ = (
        Index("ix_menu_checkouts_visit_status", "visit_session_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    checkout_id = Column(BigInteger, primary_key=True, autoincrement=True)
    visit_session_id = Column(BigInteger, ForeignKey("visit_sessions.visit_session_id"), nullable=False)
    scope = Column(
        SQLAlchemyEnum(CheckoutScope, values_callable=lambda members: [member.value for member in members]),
        nullable=False,
    )
    status = Column(
        SQLAlchemyEnum(CheckoutStatus, values_callable=lambda members: [member.value for member in members]),
        nullable=False,
        server_default=CheckoutStatus.PENDING_CONFIRMATION.value,
    )
    total_amount = Column(DECIMAL(28, 6), nullable=False)
    token_symbol = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("(UTC_TIMESTAMP())"))
