"""店舗とウォレット認証nonceの関連を操作するRepository。"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.core.utils.datetime import JST
from app.models.mysql.nonce import Nonce
from app.models.mysql.store_nonce import StoreNonce


class StoreNonceRepository:
    """店舗nonce関連の登録、検索、論理削除処理を提供する。"""

    def create_store_nonce(self, mysql_session: Session, store_nonce: StoreNonce) -> None:
        """店舗とnonceの関連をセッションへ追加する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_nonce: 登録対象の店舗nonce関連。

        Returns:
            なし。
        """
        mysql_session.add(store_nonce)

    def get_latest_available_nonce(self, mysql_session: Session, store_id: int, wallet_address: str,
                                   chain_type: str, network_name: str, expires_at: datetime) -> Nonce | None:
        """店舗で利用可能な最新のnonceを取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            wallet_address: 正規化済みウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            expires_at: 有効期限の下限日時。

        Returns:
            利用可能な最新nonce。該当するレコードがない場合はNone。
        """
        return (mysql_session.query(Nonce).join(StoreNonce, StoreNonce.nonce_id == Nonce.nonce_id).where(
            StoreNonce.store_id == store_id, StoreNonce.deleted_at.is_(None), Nonce.wallet_address == wallet_address,
            Nonce.chain_type == chain_type, Nonce.network_name == network_name, Nonce.used_at.is_(None),
            Nonce.expires_at >= expires_at).order_by(StoreNonce.store_nonce_id.desc()).first())

    def delete_store_nonce_by_nonce_id(self, mysql_session: Session, nonce_id: int) -> None:
        """nonce IDに紐づく店舗nonce関連を論理削除する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            nonce_id: 削除対象のnonce ID。

        Returns:
            なし。
        """
        now = datetime.now(JST)
        mysql_session.query(StoreNonce).where(StoreNonce.nonce_id == nonce_id).update(
            {StoreNonce.deleted_at: now, StoreNonce.updated_at: now})
