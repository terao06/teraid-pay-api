from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    func,
)

from .base_model import Base


class WalletPermit(Base):
    """ウォレットの permit 許可情報を表す ORM モデルです。"""

    __tablename__ = "wallet_permits"

    wallet_permit_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ウォレット permit 許可ID",
    )
    wallet_id = Column(
        BigInteger,
        ForeignKey("wallets.wallet_id", ondelete="CASCADE"),
        nullable=False,
        comment="ウォレットID",
    )
    token_contract_address = Column(
        String(42),
        nullable=False,
        comment="permit 対象のトークンコントラクトアドレス",
    )
    spender_address = Column(
        String(42),
        nullable=False,
        comment="allowance を許可する spender アドレス",
    )
    allowance_amount = Column(
        String(78),
        nullable=False,
        comment="permit で許可したトークン最小単位の上限金額",
    )
    permit_deadline = Column(
        DateTime,
        nullable=False,
        comment="permit 署名の有効期限",
    )
    permit_tx_hash = Column(
        String(66),
        nullable=True,
        comment="permit トランザクションハッシュ",
    )
    permitted_at = Column(
        DateTime,
        nullable=True,
        comment="permit 許可日時",
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
