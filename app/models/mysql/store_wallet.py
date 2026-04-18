from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from .base_model import Base


class StoreWallet(Base):
    """店舗ウォレット情報を表す ORM モデルです。"""

    __tablename__ = 'store_wallets'
    __table_args__ = (
        UniqueConstraint(
            'chain_type',
            'network_name',
            'wallet_address',
            name='uq_store_wallets_chain_network_address',
        ),
        Index('idx_store_wallets_store_id', 'store_id'),
        Index('idx_store_wallets_wallet_address', 'wallet_address'),
    )

    store_wallet_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment='店舗ウォレットID',
    )
    store_id = Column(
        BigInteger,
        ForeignKey('stores.store_id', ondelete='CASCADE'),
        nullable=False,
        comment='店舗ID',
    )
    wallet_address = Column(
        String(42),
        nullable=False,
        comment='ウォレットアドレス',
    )
    chain_type = Column(
        String(50),
        nullable=False,
        comment='チェーン種別(ethereum など)',
    )
    network_name = Column(
        String(50),
        nullable=False,
        comment='ネットワーク名(sepolia, mainnet など)',
    )
    token_symbol = Column(
        String(20),
        nullable=True,
        comment='受取対象トークン記号(JPYCなど)',
    )
    wallet_name = Column(
        String(255),
        nullable=True,
        comment='ウォレット表示名',
    )
    is_primary = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text('1'),
        comment='主ウォレットフラグ',
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text('1'),
        comment='有効フラグ',
    )
    verified_at = Column(
        DateTime,
        nullable=True,
        comment='署名検証完了日時',
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
        comment='作成日時',
    )
    updated_at = Column(
        DateTime,
        nullable=True,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新日時',
    )
    deleted_at = Column(
        DateTime,
        nullable=True,
        comment='削除日時',
    )
