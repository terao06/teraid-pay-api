"""会計と対象注文の紐づけを保存するMySQLモデルを提供する。"""

from sqlalchemy import BigInteger, Column, DECIMAL, ForeignKey

from .base_model import Base


class MenuCheckoutOrder(Base):
    """会計と対象注文を紐づけ、会計作成時点の注文金額を保存する。

    Args:
        kwargs: 会計ID、注文ID、注文金額の初期値。

    Returns:
        会計に含まれる注文を表すORMモデル。
    """

    __tablename__ = "menu_checkout_orders"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    checkout_id = Column(BigInteger, ForeignKey("menu_checkouts.checkout_id"), primary_key=True)
    menu_order_id = Column(BigInteger, ForeignKey("menu_orders.menu_order_id"), primary_key=True)
    order_amount = Column(DECIMAL(20, 6), nullable=False)
