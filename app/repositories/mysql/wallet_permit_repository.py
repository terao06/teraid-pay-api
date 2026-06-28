from sqlalchemy.orm import Session

from app.models.mysql.wallet_permit import WalletPermit


class WalletPermitRepository:
    """ウォレット permit 許可情報を扱うレポジトリです。"""

    def create_wallet_permit(
        self,
        mysql_session: Session,
        wallet_permit: WalletPermit,
    ) -> WalletPermit:
        """ウォレット permit 許可情報を保存します。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_permit: 保存するウォレット permit 許可情報。

        Returns:
            WalletPermit: ID を付与したウォレット permit 許可情報。
        """
        mysql_session.add(wallet_permit)
        mysql_session.flush()
        return wallet_permit
