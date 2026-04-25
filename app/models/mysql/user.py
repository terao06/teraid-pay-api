from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.sql import func

from .base_model import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    first_name = Column(String(150), nullable=True, comment='名')
    last_name = Column(String(150), nullable=True, comment='姓')
    created_at = Column(DateTime, default=func.now(), nullable=False, comment='作成日時')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment='更新日時')
    deleted_at = Column(DateTime, nullable=True, comment='削除日時')
