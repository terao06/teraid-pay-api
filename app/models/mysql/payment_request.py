from enum import Enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    String,
    Enum as SQLAlchemyEnum,
    func,
)

from .base_model import Base


class PaymentStatus(Enum):
    REQUESTED = "requested"
    SUBMITTED = "submitted"
    CONFIRMING = "confirming"
    PAID = "paid"
    TX_FAILED = "tx_failed"
    VERIFY_FAILED = "verify_failed"
    CANCELED = "canceled"
    ERROR = "error"


class PaymentRequest(Base):
    """決済リクエストを表す ORM モデル。"""

    __tablename__ = "payment_requests"

    payment_request_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="決済リクエストID",
    )

    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="店舗ID",
    )

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="ユーザーID",
    )

    store_wallet_address = Column(
        String(255),
        nullable=False,
        comment="決済時点の店舗ウォレットアドレス"
    )

    user_wallet_address = Column(
        String(255),
        nullable=False,
        comment="決済時点のユーザーウォレットアドレス"
    )

    amount = Column(
        DECIMAL(20, 6),
        nullable=False,
        comment="送金額",
    )

    token_symbol = Column(
        String(20),
        nullable=False,
        server_default="JPYC",
        comment="トークンシンボル",
    )

    chain_id = Column(
        BigInteger,
        nullable=False,
        comment="チェーンID",
    )

    status = Column(
        SQLAlchemyEnum(
            PaymentStatus,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        server_default=PaymentStatus.REQUESTED.value,
        comment="ステータス",
    )

    transaction_hash = Column(
        String(255),
        nullable=True,
        comment="トランザクションハッシュ",
    )

    expires_at = Column(
        DateTime,
        nullable=False,
        comment="有効期限",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
        comment="作成日時",
    )

    updated_at = Column(
        DateTime,
        nullable=True,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新日時",
    )

    deleted_at = Column(
        DateTime,
        nullable=True,
        comment="削除日時",
    )
