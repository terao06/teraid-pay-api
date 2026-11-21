"""注文時のオプション明細を保存する MySQL モデルを提供する。"""

from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, ForeignKey, String, text
from sqlalchemy.dialects.mysql import INTEGER

from .base_model import Base


class MenuOrderItemOption(Base):
    """注文時のオプション名、追加単価、商品1個当たりの数量を保持する。

    Args:
        kwargs: 注文明細 ID、オプション ID、名称、追加単価などの列の初期値。

    Returns:
        注文オプション明細を表す ORM インスタンス。
    """

    __tablename__ = "menu_order_item_options"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    menu_order_item_option_id = Column(BigInteger, primary_key=True, autoincrement=True)
    menu_order_item_id = Column(BigInteger, ForeignKey("menu_order_items.menu_order_item_id"), nullable=False)
    menu_option_id = Column(BigInteger, ForeignKey("menu_options.menu_option_id"), nullable=False)
    option_group_name = Column(String(100), nullable=False)
    option_name = Column(String(100), nullable=False)
    additional_price = Column(DECIMAL(20, 6), nullable=False, server_default="0")
    option_quantity = Column(INTEGER(unsigned=True), nullable=False, server_default="1")
    display_order = Column(INTEGER(unsigned=True), nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=text("(UTC_TIMESTAMP())"))
