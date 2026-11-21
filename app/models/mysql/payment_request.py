"""決済試行とその状態を保存するMySQLモデルを提供する。"""

from enum import Enum

from sqlalchemy import (
    BigInteger,
    BINARY,
    CheckConstraint,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    String,
    UniqueConstraint,
    Enum as SQLAlchemyEnum,
    func,
)

from .base_model import Base


class PaymentStatus(Enum):
    """決済試行の送信と結果確認の状態を表す。

    Args:
        value: APIとDBで使用する状態の文字列。

    Returns:
        指定された決済試行の状態。
    """

    REQUESTED = "requested"
    SUBMITTED = "submitted"
    CONFIRMING = "confirming"
    PAID = "paid"
    TX_FAILED = "tx_failed"
    VERIFY_FAILED = "verify_failed"
    CANCELED = "canceled"
    ERROR = "error"


class PaymentRequest(Base):
    """支払い先・金額・送信状態を保持し、端末の試行を会計に紐づける。

    Args:
        kwargs: 決済試行の各カラムの初期値。

    Returns:
        決済試行を表すORMモデル。
    """

    __tablename__ = "payment_requests"
    __table_args__ = (
        UniqueConstraint("checkout_id", "idempotency_key_hash", name="uq_payment_requests_checkout_key"),
        CheckConstraint(
            "(checkout_id IS NULL AND checkout_transaction_hash IS NULL) "
            "OR (checkout_id IS NOT NULL AND transaction_hash IS NULL)",
            name="ck_payment_requests_transaction_hash_scope",
        ),
    )

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

    checkout_id = Column(BigInteger, ForeignKey("menu_checkouts.checkout_id"), nullable=True)
    idempotency_key_hash = Column(BINARY(32), nullable=True)

    amount = Column(
        DECIMAL(28, 6),
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

    checkout_transaction_hash = Column(
        String(66),
        nullable=True,
        comment="端末の会計決済で送信前に確定するトランザクションハッシュ",
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
