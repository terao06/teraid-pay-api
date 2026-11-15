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


class MenuOptionGroup(Base):
    """メニュー商品のオプショングループを表す ORM モデル。"""

    __tablename__ = "menu_option_groups"

    menu_option_group_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="オプショングループID",
    )
    menu_item_id = Column(
        BigInteger,
        ForeignKey("menu_items.menu_item_id", ondelete="CASCADE"),
        nullable=False,
        comment="対象商品ID",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="オプショングループ名",
    )
    min_selections = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="最小選択数",
    )
    max_selections = Column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="最大選択数",
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
