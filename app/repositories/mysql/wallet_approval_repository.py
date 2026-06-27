from sqlalchemy.orm import Session

from app.models.mysql.wallet_approval import WalletApproval


class WalletApprovalRepository:
    """ウォレット承認情報を扱うレポジトリです。"""

    def create_wallet_approval(
        self,
        mysql_session: Session,
        wallet_approval: WalletApproval,
    ) -> WalletApproval:
        """ウォレット承認情報を保存します。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_approval: 保存するウォレット承認情報。

        Returns:
            WalletApproval: ID を付与したウォレット承認情報。
        """
        mysql_session.add(wallet_approval)
        mysql_session.flush()
        return wallet_approval
