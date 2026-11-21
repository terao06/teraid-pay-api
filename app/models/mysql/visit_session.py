"""端末の来店セッションを記録するMySQLモデルを提供する。"""

from enum import Enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)

from .base_model import Base


class VisitSessionStatus(Enum):
    """来店セッションに保存する状態を定義する。

    Args:
        なし。

    Returns:
        注文受付中、決済処理中、または終了済みを表す列挙値。
    """

    ACTIVE = "active"
    CHECKOUT_PROCESSING = "checkout_processing"
    CLOSED = "closed"


class VisitSession(Base):
    """認証済み端末で開始した来店セッションを永続化する。

    Args:
        device_id: セッションを開始した端末のID。
        start_request_id: 端末が生成した開始要求ID。
        status: セッションの状態。
        started_at: 開始日時。
        ended_at: 終了日時。進行中の場合はNone。

    Returns:
        来店セッションを表すORMモデル。
    """

    __tablename__ = "visit_sessions"
    __table_args__ = (
        UniqueConstraint("device_id", "start_request_id", name="uq_visit_sessions_device_request"),
        Index("ix_visit_sessions_device_status", "device_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    visit_session_id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(BigInteger, ForeignKey("devices.device_id"), nullable=False)
    start_request_id = Column(String(64, collation="utf8mb4_0900_bin"), nullable=False)
    status = Column(
        SQLAlchemyEnum(
            VisitSessionStatus,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        server_default=VisitSessionStatus.ACTIVE.value,
    )
    started_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    ended_at = Column(DateTime, nullable=True)
