from datetime import datetime

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.models.mysql.wallet import Wallet


class WalletRepository:
    def create_wallet(self, mysql_session: Session, wallet: Wallet) -> Wallet:
        """ウォレットを登録する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet: 登録対象ウォレット。

        Returns:
            wallet: 登録済みウォレット。
        """
        mysql_session.add(wallet)
        mysql_session.flush()
        return wallet

    def get_wallet_by_id(self, mysql_session: Session, wallet_id: int) -> Wallet | None:
        """ウォレットを取得。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_id: 検索対象のウォレットID

        Returns:
            wallet: 登録済みウォレット。
        """
        return (
            mysql_session.query(Wallet)
            .where(Wallet.wallet_id == wallet_id)
            .where(Wallet.deleted_at.is_(None))
        ).first()

    def update_wallet(self, mysql_session: Session, wallet: Wallet) -> Wallet:
        """ウォレットを更新する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet: 更新対象ウォレット。

        Returns:
            wallet: 更新済みウォレット。
        """
        wallet.updated_at = datetime.now()
        mysql_session.add(wallet)
        mysql_session.flush()
        return wallet

    def get_wallet_by_address(self, mysql_session: Session, wallet_address: str) -> Wallet | None:
        """ウォレットアドレスに紐づくウォレットを取得。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_address: 検索対象のウォレットアドレス

        Returns:
            wallet: 登録済みウォレット。
        """
        return (
            mysql_session.query(Wallet)
            .where(Wallet.wallet_address == wallet_address)
            .where(Wallet.deleted_at.is_(None))
        ).first()

    def delete_wallet_by_wallet_id(self, mysql_session: Session, wallet_id: int) -> None:
        """ウォレットを削除する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet: 登録対象ウォレット。

        Returns:
            wallet: 登録済みウォレット。
        """
        now = datetime.now(JST)
        (
            mysql_session.query(Wallet)
            .where(Wallet.wallet_id == wallet_id)
            .update({Wallet.deleted_at: now, Wallet.updated_at: now})
        )
