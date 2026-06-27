from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    func,
)

from .base_model import Base


class WalletApproval(Base):
    """ウォレットの決済承認情報を表す ORM モデルです。"""

    __tablename__ = "wallet_approvals"

    wallet_approval_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ウォレット承認ID",
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
        comment="承認対象のトークンコントラクトアドレス",
    )
    spender_address = Column(
        String(42),
        nullable=False,
        comment="allowance を許可する spender アドレス",
    )
    allowance_amount = Column(
        String(78),
        nullable=False,
        comment="トークン最小単位の承認上限金額",
    )
    permit_deadline = Column(
        DateTime,
        nullable=False,
        comment="permit 署名の有効期限",
    )
    approval_tx_hash = Column(
        String(66),
        nullable=True,
        comment="承認トランザクションハッシュ",
    )
    approved_at = Column(
        DateTime,
        nullable=True,
        comment="承認日時",
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