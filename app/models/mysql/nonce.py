from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    String,
    func,
)

from .base_model import Base


class Nonce(Base):
    """ウォレット署名用 nonce を表す ORM モデル。"""

    __tablename__ = 'nonces'
    nonce_id = Column(BigInteger, primary_key=True, autoincrement=True)
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
