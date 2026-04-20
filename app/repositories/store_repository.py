from datetime import datetime

from sqlalchemy.orm import Session

from app.models.mysql.store import Store
from app.models.mysql.wallet import Wallet
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_nonce import StoreNonce
from app.models.dtos.store_wallet_dto import StoreWalletDto
from app.models.mysql.nonce import Nonce


class StoreRepository:
    """店舗ウォレット情報を取得するリポジトリです。"""

    def get_store_wallet(self, session: Session, store_id: int) -> StoreWalletDto | None:
        """条件に一致する店舗ウォレット一覧を取得します。
        Args:
            session: SQLAlchemy のセッションです。
            store_id: 絞り込み対象の店舗 ID です。

        Returns:
            store_wallet_list: 店舗ウォレット DTO の一覧です。
        """
        query = session.query(
            StoreWallet.store_wallet_id,
            StoreWallet.store_id,
            Wallet.wallet_address,
            Wallet.chain_type,
            Wallet.network_name,
            Wallet.is_active,
            Wallet.verified_at,
            Wallet.created_at,
            Wallet.updated_at
        ).join(
            Wallet,
            Wallet.wallet_id == StoreWallet.wallet_id
        ).join(
            Store,
            StoreWallet.store_id == Store.store_id
        ).where(
            Store.deleted_at.is_(None),
            StoreWallet.deleted_at.is_(None),
            Wallet.deleted_at.is_(None)
        )
        if store_id:
            query = query.where(
                Store.store_id == store_id
            )

        store_wallet = query.first()

        if store_wallet is None:
            return None

        return StoreWalletDto(
            store_wallet_id=store_wallet.store_wallet_id,
            store_id=store_wallet.store_id,
            wallet_address=store_wallet.wallet_address,
            chain_type=store_wallet.chain_type,
            network_name=store_wallet.network_name,
            is_active=store_wallet.is_active,
            verified_at=store_wallet.verified_at,
            created_at=store_wallet.created_at,
            updated_at=store_wallet.updated_at,
        )

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
    
    def create_nonce(self, session: Session, nonce: Nonce) -> Nonce:
        """nonceを作成する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            取得した店舗情報。存在しない場合は `None`。
        """
        session.add(nonce)
        session.flush()
        return nonce
    
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
            .where(Nonce.wallet_address == wallet_address)
            .where(Nonce.chain_type == chain_type)
            .where(Nonce.network_name == network_name)
            .where(Nonce.used_at.is_(None))
            .where(Nonce.expires_at >= expires_at)
            .order_by(StoreNonce.store_nonce_id.desc())
        ).first()

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

    def update_store_wallet_nonce(self, session: Session, nonce: Nonce) -> None:
        """更新済み nonce を保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_wallet_nonce: 更新対象の nonce エンティティ。

        Returns:
            なし。
        """
        session.add(nonce)
