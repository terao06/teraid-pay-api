"""店舗に設置する決済デバイスのORMモデルを提供する。"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, func, text

from .base_model import Base


class Device(Base):
    """店舗に紐付く決済デバイスを表すORMモデル。"""

    __tablename__ = "devices"

    device_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="デバイスID",
    )
    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="設置店舗ID",
    )
    device_name = Column(
        String(100),
        nullable=False,
        comment="デバイス名",
    )
    device_uuid = Column(
        String(36),
        nullable=False,
        unique=True,
        comment="デバイスUUID",
    )
    activation_code_hash = Column(
        String(64),
        nullable=True,
        unique=True,
        comment="有効化コードのSHA-256ハッシュ",
    )
    activation_expires_at = Column(
        DateTime,
        nullable=True,
        comment="有効化コードの有効期限",
    )
    device_credential_hash = Column(
        String(255),
        nullable=True,
        comment="長期端末認証情報のハッシュ",
    )
    activated_at = Column(
        DateTime,
        nullable=True,
        comment="初回有効化日時",
    )
    last_authenticated_at = Column(
        DateTime,
        nullable=True,
        comment="最終認証日時",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
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

