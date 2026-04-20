from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    func,
)

from .base_model import Base


class StoreWallet(Base):
    """店舗とウォレットの紐づきを表す ORM モデル。"""

    __tablename__ = "store_wallets"

    store_wallet_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="店舗ウォレットID",
    )
    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="店舗ID",
    )
    wallet_id = Column(
        BigInteger,
        ForeignKey("wallets.wallet_id", ondelete="CASCADE"),
        nullable=False,
        comment="ウォレットID",
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
