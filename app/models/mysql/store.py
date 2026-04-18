from sqlalchemy import Column, String, BigInteger, DateTime, func
from .base_model import Base


class Store(Base):
    """店舗情報を表す ORM モデルです。"""

    __tablename__ = 'stores'
    store_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255))
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    deleted_at = Column(DateTime, nullable=True)
