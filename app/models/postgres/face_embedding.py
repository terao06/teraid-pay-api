from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    func,
    text,
    Column,
    Enum as SQLEnum
)

from .base_model import Base
from .vector import Vector


class ExtensionType(Enum):
    JPEG = "jpeg"
    PNG = "png"
    JPG = "jpg"


class FaceEmbedding(Base):
    """PostgreSQL pgvector に保存する顔特徴量モデル。"""

    __tablename__ = "face_embeddings"

    face_embedding_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="顔特徴量ID",
    )
    user_id = Column(
        BigInteger,
        nullable=False,
        comment="ユーザーID",
    )
    embedding = Column(
        Vector(512),
        nullable=False,
        comment="512次元の顔特徴量ベクトル",
    )
    extension_type = Column(
        SQLEnum(
            ExtensionType,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            name="extension_type",
        ),
        nullable=False,
        comment="画像の拡張子",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="有効フラグ",
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
