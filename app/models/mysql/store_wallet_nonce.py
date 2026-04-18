from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)

from .base_model import Base


class StoreWalletNonce(Base):
    """ウォレット署名用 nonce を表す ORM モデル。"""

    __tablename__ = 'store_wallet_nonces'
    __table_args__ = (
        Index('idx_store_wallet_nonces_store_id', 'store_id'),
        Index('idx_store_wallet_nonces_wallet_address', 'wallet_address'),
        Index('idx_store_wallet_nonces_expires_at', 'expires_at'),
        Index(
            'idx_store_wallet_nonces_chain_network',
            'chain_type',
            'network_name',
        ),
    )

    store_wallet_nonce_id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(
        BigInteger,
        ForeignKey('stores.store_id', ondelete='CASCADE'),
        nullable=False,
    )
    wallet_address = Column(String(42), nullable=False)
    chain_type = Column(String(50), nullable=False)
    network_name = Column(String(50), nullable=False)
    nonce = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True, default=None)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
    )
    updated_at = Column(
        DateTime,
        nullable=True,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
