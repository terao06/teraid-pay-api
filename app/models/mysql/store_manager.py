from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    func,
    text,
)

from .base_model import Base


class StoreManager(Base):
    """店舗管理者を表す ORM モデル。"""

    __tablename__ = "store_managers"

    store_manager_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="店舗管理者ID",
    )
    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="所属店舗ID",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="管理者名",
    )
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="ログイン・連絡用メールアドレス",
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="パスワードハッシュ",
    )
    roll_id = Column(
        BigInteger,
        nullable=False,
        comment="権限ロールID",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="利用可能フラグ",
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
        nullable=False,
        default=func.current_timestamp(),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新日時",
    )
    deleted_at = Column(
        DateTime,
        nullable=True,
        comment="論理削除日時",
    )
