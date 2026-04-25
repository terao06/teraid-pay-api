from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func

from .base_model import Base


class UserNonce(Base):
    """ユーザーとnonceの紐づきを表す ORM モデル。"""

    __tablename__ = "user_nonces"

    user_nonce_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ユーザーnonce ID",
    )

    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="ユーザーID",
    )

    nonce_id = Column(
        BigInteger,
        ForeignKey("nonces.nonce_id", ondelete="CASCADE"),
        nullable=False,
        comment="nonce ID",
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
