from datetime import datetime

from sqlalchemy.orm import Session

from app.models.mysql.store import Store
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_wallet_nonce import StoreWalletNonce
from app.models.dtos.store_wallet_dto import StoreWalletDto


class StoreRepository:
    """店舗ウォレット情報を取得するリポジトリです。"""

    def get_store_wallet_list(self, session: Session, store_id: int | None = None) -> list[StoreWalletDto]:
        """条件に一致する店舗ウォレット一覧を取得します。
        Args:
            session: SQLAlchemy のセッションです。
            store_id: 絞り込み対象の店舗 ID です。未指定時は全店舗を対象にします。

        Returns:
            store_wallet_list: 店舗ウォレット DTO の一覧です。
        """
        query = session.query(
            StoreWallet.store_wallet_id,
            StoreWallet.store_id,
            StoreWallet.wallet_address,
            StoreWallet.chain_type,
            StoreWallet.network_name,
            StoreWallet.is_active,
            StoreWallet.verified_at,
            StoreWallet.created_at,
            StoreWallet.updated_at
        ).join(
            Store,
            StoreWallet.store_id == Store.store_id
        ).where(
            Store.deleted_at.is_(None),
            StoreWallet.deleted_at.is_(None)
        )
        if store_id:
            query = query.where(
                Store.store_id == store_id
            )

        result_store_wallet = query.all()

        store_wallet_list = []
        for store_wallet in result_store_wallet:
            store_wallet_list.append(
                StoreWalletDto(
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
            )
        return store_wallet_list

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
    
    def create_store_wallet_nonce(self, session: Session, store_wallet_nonce: StoreWalletNonce) -> None:
        """ウォレット nonce を保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_wallet_nonce: 保存するウォレット nonce エンティティ。

        Returns:
            なし。
        """
        session.add(store_wallet_nonce)
    
    def get_store_wallet_by_address(
        self,
        session: Session,
        wallet_address: str,
        chain_type: str,
        network_name: str,
    ) -> StoreWallet | None:
        """ウォレットアドレスに紐づく店舗ウォレットを取得する。

        Args:
            session: SQLAlchemy のセッション。
            wallet_address: 検索対象のウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            該当する店舗ウォレット。存在しない場合は `None`。
        """
        return (
            session.query(StoreWallet)
            .where(StoreWallet.wallet_address == wallet_address)
            .where(StoreWallet.chain_type == chain_type)
            .where(StoreWallet.network_name == network_name)
            .where(StoreWallet.deleted_at.is_(None))
        ).first()
    
    def get_latest_available_nonce(
        self,
        session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        expires_at: datetime) -> StoreWalletNonce | None:
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
            session.query(StoreWalletNonce)
            .where(StoreWalletNonce.store_id == store_id)
            .where(StoreWalletNonce.wallet_address == wallet_address)
            .where(StoreWalletNonce.chain_type == chain_type)
            .where(StoreWalletNonce.network_name == network_name)
            .where(StoreWalletNonce.used_at.is_(None))
            .where(StoreWalletNonce.expires_at >= expires_at)
            .order_by(StoreWalletNonce.store_wallet_nonce_id.desc())
        ).first()

    def unset_primary_wallets(self, session: Session, store_id: int) -> None:
        """店舗の主ウォレット設定を解除する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            なし。
        """
        (
            session.query(StoreWallet)
            .where(StoreWallet.store_id == store_id)
            .where(StoreWallet.deleted_at.is_(None))
            .where(StoreWallet.is_primary.is_(True))
            .update(
                {
                    StoreWallet.is_primary: False,
                    StoreWallet.updated_at: datetime.now(),
                },
                synchronize_session=False,
            )
        )
        
    def create_store_wallet(self, session: Session, store_wallet: StoreWallet) -> None:
        """店舗ウォレットを保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_wallet: 保存する店舗ウォレット。

        Returns:
            なし。
        """
        session.add(store_wallet)

    def update_store_wallet_nonce(self, session: Session, store_wallet_nonce: StoreWalletNonce) -> None:
        """更新済み nonce を保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_wallet_nonce: 更新対象の nonce エンティティ。

        Returns:
            なし。
        """
        session.add(store_wallet_nonce)
