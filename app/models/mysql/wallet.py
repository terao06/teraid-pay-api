from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    String,
    func,
    text,
)

from .base_model import Base


class Wallet(Base):
    """ウォレット情報を表す ORM モデル。"""

    __tablename__ = "wallets"

    wallet_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ウォレットID",
    )
    wallet_address = Column(
        String(42),
        nullable=False,
        comment="ウォレットアドレス",
    )
    chain_type = Column(
        String(50),
        nullable=False,
        comment="チェーン種別",
    )
    network_name = Column(
        String(50),
        nullable=False,
        comment="ネットワーク名",
    )
    token_symbol = Column(
        String(20),
        nullable=False,
        comment="トークンシンボル",
    )
    chain_id = Column(
        BigInteger,
        nullable=False,
        comment="チェーンID",
    )
    wallet_name = Column(
        String(255),
        nullable=True,
        comment="ウォレット表示名",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="有効フラグ",
    )
    verified_at = Column(
        DateTime,
        nullable=True,
        comment="検証完了日時",
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
