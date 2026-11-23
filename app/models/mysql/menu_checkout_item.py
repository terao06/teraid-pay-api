"""会計作成時点の対象注文明細、数量、金額を保存するMySQLモデルを提供する。"""

from sqlalchemy import BigInteger, Column, DECIMAL, ForeignKey
from sqlalchemy.dialects.mysql import INTEGER

from .base_model import Base


class MenuCheckoutItem(Base):
    """会計に含まれる注文明細と、その会計で支払う数量・金額を保持する。

    Args:
        kwargs: 会計ID、注文明細ID、対象数量、明細金額の初期値。

    Returns:
        会計明細を表すORMモデル。
    """

    __tablename__ = "menu_checkout_items"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    checkout_id = Column(BigInteger, ForeignKey("menu_checkouts.checkout_id"), primary_key=True)
    menu_order_item_id = Column(BigInteger, ForeignKey("menu_order_items.menu_order_item_id"), primary_key=True)
    quantity = Column(INTEGER(unsigned=True), nullable=False)
    line_amount = Column(DECIMAL(20, 6), nullable=False)
