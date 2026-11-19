"""店舗管理者の失効済みアクセストークンを管理する。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base_model import Base


class StoreManagerRevokedToken(Base):
    """失効したJWTの識別子と有効期限をUTCで保持する。

    Args:
        jti: 失効したJWTの一意な識別子。
        store_manager_id: JWTを発行した店舗管理者のID。
        expires_at: JWTの有効期限（UTC）。
        created_at: 失効の登録日時（UTC）。

    Returns:
        失効レコードのORMインスタンス。
    """

    __tablename__ = "store_manager_revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    store_manager_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("store_managers.store_manager_id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
