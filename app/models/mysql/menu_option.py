from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)

from .base_model import Base


class MenuOption(Base):
    """メニュー商品の選択可能なオプションを表す ORM モデル。"""

    __tablename__ = "menu_options"

    menu_option_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="オプションID",
    )
    menu_option_group_id = Column(
        BigInteger,
        ForeignKey("menu_option_groups.menu_option_group_id", ondelete="CASCADE"),
        nullable=False,
        comment="オプショングループID",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="オプション名",
    )
    additional_price = Column(
        DECIMAL(20, 6),
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="追加料金",
    )
    display_order = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="表示順",
    )
    is_available = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
        comment="選択可能フラグ",
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
