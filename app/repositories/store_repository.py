from datetime import datetime

from sqlalchemy.orm import Session

from app.models.mysql.store import Store
from app.models.mysql.wallet import Wallet
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_nonce import StoreNonce
from app.models.mysql.nonce import Nonce
from app.core.utils.datetime import JST


class StoreRepository:
    """店舗ウォレット情報を取得するリポジトリです。"""

    def get_store_wallet(self, session: Session, store_id: int) -> Wallet | None:
        """条件に一致する店舗ウォレット一覧を取得します。
        Args:
            session: SQLAlchemy のセッションです。
            store_id: 絞り込み対象の店舗 ID です。

        Returns:
            Wallet: ウォレット情報。
        """
        return session.query(Wallet
        ).join(
            StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id
        ).join(
            Store, StoreWallet.store_id == Store.store_id
        ).where(
            Store.store_id == store_id,
            Store.deleted_at.is_(None),
            StoreWallet.deleted_at.is_(None),
            Wallet.deleted_at.is_(None)
        ).first()

    def get_store_by_id(self, session: Session, store_id: int) -> Store | None:
        """店舗 ID から店舗情報を取得する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            取得した店舗情報。存在しない場合は `None`。
        """
        return session.query(Store).where(
            Store.store_id == store_id,
            Store.deleted_at.is_(None)
        ).one_or_none()

    def create_store_nonce(self, session: Session, store_nonce: StoreNonce) -> None:
        """店舗 nonce を保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_nonce: 保存する店舗 nonce エンティティ。

        Returns:
            なし。
        """
        session.add(store_nonce)
    
    def get_wallet_by_store_id(
        self,
        session: Session,
        store_id: int,
        chain_type: str,
        network_name: str,
    ) -> Wallet | None:
        """ウォレットアドレスに紐づく店舗ウォレットを取得する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 店舗ID
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            該当する店舗ウォレット。存在しない場合は `None`。
        """
        return (
            session.query(Wallet)
            .join(StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id)
            .where(StoreWallet.store_id == store_id)
            .where(Wallet.chain_type == chain_type)
            .where(Wallet.network_name == network_name)
            .where(Wallet.deleted_at.is_(None))
        ).first()

    def get_latest_available_nonce(
        self,
        session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        expires_at: datetime) -> Nonce | None:
        """利用可能な最新の nonce を取得する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            expires_at: 有効期限の下限日時。

        Returns:
            利用可能な最新 nonce。存在しない場合は `None`。
        """

        return (
            session.query(Nonce)
            .join(StoreNonce, StoreNonce.nonce_id == Nonce.nonce_id)
            .where(StoreNonce.store_id == store_id)
            .where(StoreNonce.deleted_at.is_(None))
            .where(Nonce.wallet_address == wallet_address)
            .where(Nonce.chain_type == chain_type)
            .where(Nonce.network_name == network_name)
            .where(Nonce.used_at.is_(None))
            .where(Nonce.expires_at >= expires_at)
            .order_by(StoreNonce.store_nonce_id.desc())
        ).first()

    def create_store_wallet(self, session: Session, store_wallet: StoreWallet) -> None:
        """店舗ウォレットを保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_wallet: 保存する店舗ウォレット。

        Returns:
            なし。
        """
        session.add(store_wallet)
        session.flush()
        return store_wallet

    def delete_store_nonce_by_nonce_id(self, session: Session, nonce_id: int) -> None:
        """対象のnonceを論理削除する。

        Args:
            session: SQLAlchemy のセッション。
            nonce_id: nonce id

        Returns:
            なし。
        
        """
        now = datetime.now(JST)
        (
            session.query(StoreNonce)
            .where(StoreNonce.nonce_id == nonce_id)
            .update({StoreNonce.deleted_at: now, StoreNonce.updated_at: now})
        )
    
    def delete_store_wallet_by_wallet_id(self, session: Session, wallet_id: int) -> None:
        """wallet_idを指定し対象の店舗ウォレット紐づけを論理削除する。

        Args:
            session: SQLAlchemy のセッション。
            wallet_id: wallet_id

        Returns:
            なし。
        
        """
        now = datetime.now(JST)
        (
            session.query(StoreWallet)
            .where(StoreWallet.wallet_id == wallet_id)
            .update({StoreWallet.deleted_at: now, StoreWallet.updated_at: now})
        )
