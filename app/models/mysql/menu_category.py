from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)

from .base_model import Base


class MenuCategory(Base):
    """店舗ごとのメニューカテゴリーを表す ORM モデル。"""

    __tablename__ = "menu_categories"

    menu_category_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="カテゴリーID",
    )
    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="店舗ID",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="カテゴリー名",
    )
    image_extension = Column(
        String(10),
        nullable=False,
        comment="カテゴリー画像の拡張子",
    )
    display_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="表示順",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
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
    deleted_at = Column(
        DateTime,
        nullable=True,
        comment="論理削除日時",
    )
