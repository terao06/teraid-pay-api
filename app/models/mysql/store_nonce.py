from sqlalchemy import BigInteger, Column, ForeignKey

from .base_model import Base


class StoreNonce(Base):
    """店舗とnonceの紐づきを表す ORM モデル。"""

    __tablename__ = "store_nonces"

    store_nonce_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="店舗nonce ID",
    )

    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="店舗ID",
    )

    nonce_id = Column(
        BigInteger,
        ForeignKey("nonces.nonce_id", ondelete="CASCADE"),
        nullable=False,
        comment="nonce ID",
    )