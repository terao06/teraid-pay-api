from datetime import datetime

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
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
    
    def get_wallet_by_address(self, session: Session, wallet_address: str) -> Wallet | None:
        """ウォレットアドレスに紐づくウォレットを取得。

        Args:
            session: SQLAlchemy のセッション。
            wallet_address: 検索対象のウォレットアドレス

        Returns:
            wallet: 登録済みウォレット。
        """
        return (
            session.query(Wallet)
            .where(Wallet.wallet_address == wallet_address)
            .where(Wallet.deleted_at.is_(None))
        ).first()

    def delete_wallet_by_wallet_id(self, session: Session, wallet_id: int) -> None:
        """ウォレットを削除する。

        Args:
            session: SQLAlchemy のセッション。
            wallet: 登録対象ウォレット。

        Returns:
            wallet: 登録済みウォレット。
        """
        now = datetime.now(JST)
        (
            session.query(Wallet)
            .where(Wallet.wallet_id == wallet_id)
            .update({Wallet.deleted_at: now, Wallet.updated_at: now})
        )
