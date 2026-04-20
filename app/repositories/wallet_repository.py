from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet


class WalletRepository:
    def create_wallet(self, session: Session, wallet: Wallet) -> Wallet:
        """ウォレットを登録する。

        Args:
            session: SQLAlchemy のセッション。
            wallet: 登録対象ウォレット。

        Returns:
            wallet: 登録済みウォレット。
        """
        session.add(wallet)
        session.flush()
        return wallet
