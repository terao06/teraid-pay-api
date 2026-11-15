from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)

from .base_model import Base


class MenuItem(Base):
    """店舗で販売するメニュー商品を表す ORM モデル。"""

    __tablename__ = "menu_items"

    menu_item_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="商品ID",
    )
    store_id = Column(
        BigInteger,
        ForeignKey("stores.store_id", ondelete="CASCADE"),
        nullable=False,
        comment="店舗ID",
    )
    menu_category_id = Column(
        BigInteger,
        ForeignKey("menu_categories.menu_category_id"),
        nullable=True,
        comment="カテゴリーID",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="商品名",
    )
    description = Column(
        Text,
        nullable=True,
        comment="商品説明",
    )
    price = Column(
        DECIMAL(20, 6),
        nullable=False,
        comment="基本価格",
    )
    token_symbol = Column(
        String(20),
        nullable=False,
        server_default="JPYC",
        comment="トークンシンボル",
    )
    image_extension = Column(
        String(10),
        nullable=False,
        comment="商品画像の拡張子",
    )
    is_available = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="販売可能フラグ",
    )
    display_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="表示順",
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
