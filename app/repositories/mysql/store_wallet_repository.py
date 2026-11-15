"""店舗ウォレットと店舗情報を操作するRepository。"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.core.utils.datetime import JST
from app.models.mysql.store import Store
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet
from app.repositories.mysql.store_nonce_repository import StoreNonceRepository


class StoreWalletRepository(StoreNonceRepository):
    """店舗ウォレット関連とウォレット認証用nonceの永続化処理を提供する。"""
    def get_store_wallet_link(self, mysql_session: Session, store_id: int, wallet_id: int) -> StoreWallet | None:
        """店舗IDとウォレットIDに一致する有効な関連を取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            wallet_id: 対象ウォレットID。

        Returns:
            店舗ウォレット関連。該当するレコードがない場合はNone。
        """
        return mysql_session.query(StoreWallet).filter(
            StoreWallet.store_id == store_id, StoreWallet.wallet_id == wallet_id,
            StoreWallet.deleted_at.is_(None)).one_or_none()

    def get_store_wallet(self, mysql_session: Session, store_id: int) -> Wallet | None:
        """店舗に紐づく有効なウォレットを取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。

        Returns:
            店舗ウォレット。該当するレコードがない場合はNone。
        """
        return (mysql_session.query(Wallet).join(StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id)
                .join(Store, StoreWallet.store_id == Store.store_id).where(
                    Store.store_id == store_id, Store.deleted_at.is_(None), StoreWallet.deleted_at.is_(None),
                    Wallet.deleted_at.is_(None)).first())

    def get_wallet_by_store_id(self, mysql_session: Session, store_id: int, chain_type: str,
                               network_name: str, chain_id: int) -> Wallet | None:
        """店舗とネットワーク条件に一致するウォレットを取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            chain_id: チェーンID。

        Returns:
            条件に一致するウォレット。存在しない場合はNone。
        """
        return (mysql_session.query(Wallet).join(StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id).where(
            StoreWallet.store_id == store_id, StoreWallet.deleted_at.is_(None), Wallet.chain_type == chain_type,
            Wallet.network_name == network_name, Wallet.chain_id == chain_id, Wallet.deleted_at.is_(None)).first())

    def create_store_wallet(self, mysql_session: Session, store_wallet: StoreWallet) -> StoreWallet:
        """店舗ウォレット関連を追加してIDを確定する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_wallet: 登録対象の店舗ウォレット関連。

        Returns:
            IDが付与された店舗ウォレット関連。
        """
        mysql_session.add(store_wallet); mysql_session.flush(); return store_wallet

    def delete_store_wallet_by_wallet_id(self, mysql_session: Session, wallet_id: int) -> None:
        """ウォレットIDに紐づく店舗ウォレット関連を論理削除する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            wallet_id: 削除対象のウォレットID。

        Returns:
            なし。
        """
        now = datetime.now(JST)
        mysql_session.query(StoreWallet).where(StoreWallet.wallet_id == wallet_id).update(
            {StoreWallet.deleted_at: now, StoreWallet.updated_at: now})
