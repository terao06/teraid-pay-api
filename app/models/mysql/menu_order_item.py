"""注文時の商品明細を保存する MySQL モデルを提供する。"""

from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, ForeignKey, String, text
from sqlalchemy.dialects.mysql import INTEGER

from .base_model import Base


class MenuOrderItem(Base):
    """注文時の商品名、単価、数量を保持する。

    Args:
        kwargs: 注文 ID、商品 ID、商品名、単価、数量、明細金額などの列の初期値。

    Returns:
        注文明細を表す ORM インスタンス。
    """

    __tablename__ = "menu_order_items"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    menu_order_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    menu_order_id = Column(BigInteger, ForeignKey("menu_orders.menu_order_id"), nullable=False)
    menu_item_id = Column(BigInteger, ForeignKey("menu_items.menu_item_id"), nullable=False)
    menu_item_name = Column(String(255), nullable=False)
    unit_price = Column(DECIMAL(20, 6), nullable=False)
    quantity = Column(INTEGER(unsigned=True), nullable=False)
    line_amount = Column(DECIMAL(20, 6), nullable=False)
    display_order = Column(INTEGER(unsigned=True), nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=text("(UTC_TIMESTAMP())"))
