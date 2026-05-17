from datetime import datetime

from sqlalchemy.orm import Session

from app.models.mysql.user import User
from app.models.mysql.wallet import Wallet
from app.models.mysql.user_wallet import UserWallet
from app.models.mysql.user_nonce import UserNonce
from app.models.mysql.nonce import Nonce
from app.core.utils.datetime import JST


class UserRepository:
    """ユーザーウォレット情報を取得するリポジトリです。"""

    def get_user_wallet(self, session: Session, user_id: int) -> Wallet | None:
        """ユーザーに紐づくウォレットを取得します。
        Args:
            session: SQLAlchemy のセッションです。
            user_id: 絞り込み対象のユーザー ID です。

        Returns:
            Wallet: ウォレット情報。
        """
        return session.query(Wallet
        ).join(
            UserWallet, Wallet.wallet_id == UserWallet.wallet_id
        ).join(
            User, UserWallet.user_id == User.user_id
        ).where(
            User.user_id == user_id,
            User.deleted_at.is_(None),
            UserWallet.deleted_at.is_(None),
            Wallet.deleted_at.is_(None)
        ).first()

    def get_user_by_id(self, session: Session, user_id: int) -> User | None:
        """ユーザー ID から店舗情報を取得する。

        Args:
            session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。

        Returns:
            取得したユーザー情報。存在しない場合は `None`。
        """
        return session.query(User).where(
            User.user_id == user_id,
            User.deleted_at.is_(None)
        ).one_or_none()

    def create_user_nonce(self, session: Session, user_nonce: UserNonce) -> None:
        """店舗 nonce を保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            user_nonce: 保存するユーザー nonce エンティティ。

        Returns:
            なし。
        """
        session.add(user_nonce)

    def get_wallet_by_user_id(
        self,
        session: Session,
        user_id: int,
        chain_type: str,
        network_name: str,
        chain_id: int,
    ) -> Wallet | None:
        """ウォレットアドレスに紐づくユーザーウォレットを取得する。

        Args:
            session: SQLAlchemy のセッション。
            user_id: ユーザーID
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            該当するユーザーウォレット。存在しない場合は `None`。
        """
        return (
            session.query(Wallet)
            .join(UserWallet, Wallet.wallet_id == UserWallet.wallet_id)
            .where(UserWallet.user_id == user_id)
            .where(UserWallet.deleted_at.is_(None))
            .where(Wallet.chain_type == chain_type)
            .where(Wallet.network_name == network_name)
            .where(Wallet.chain_id == chain_id)
            .where(Wallet.deleted_at.is_(None))
        ).first()

    def get_latest_available_nonce(
        self,
        session: Session,
        user_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        expires_at: datetime) -> Nonce | None:
        """利用可能な最新の nonce を取得する。

        Args:
            session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            expires_at: 有効期限の下限日時。

        Returns:
            利用可能な最新 nonce。存在しない場合は `None`。
        """

        return (
            session.query(Nonce)
            .join(UserNonce, UserNonce.nonce_id == Nonce.nonce_id)
            .where(UserNonce.user_id == user_id)
            .where(UserNonce.deleted_at.is_(None))
            .where(Nonce.wallet_address == wallet_address)
            .where(Nonce.chain_type == chain_type)
            .where(Nonce.network_name == network_name)
            .where(Nonce.used_at.is_(None))
            .where(Nonce.expires_at >= expires_at)
            .order_by(UserNonce.user_nonce_id.desc())
        ).first()

    def create_user_wallet(self, session: Session, user_wallet: UserWallet) -> None:
        """ユーザーウォレットを保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            user_wallet: 保存する店舗ウォレット。

        Returns:
            なし。
        """
        session.add(user_wallet)
        session.flush()
        return user_wallet

    def delete_user_nonce_by_nonce_id(self, session: Session, nonce_id: int) -> None:
        """対象のユーザーnonceを論理削除する。

        Args:
            session: SQLAlchemy のセッション。
            nonce_id: nonce id

        Returns:
            なし。
        
        """
        now = datetime.now(JST)
        (
            session.query(UserNonce)
            .where(UserNonce.nonce_id == nonce_id)
            .update({UserNonce.deleted_at: now, UserNonce.updated_at: now})
        )
    
    def delete_user_wallet_by_wallet_id(self, session: Session, wallet_id: int) -> None:
        """wallet_idを指定し対象の店舗ウォレット紐づけを論理削除する。

        Args:
            session: SQLAlchemy のセッション。
            wallet_id: wallet_id

        Returns:
            なし。
        
        """
        now = datetime.now(JST)
        (
            session.query(UserWallet)
            .where(UserWallet.wallet_id == wallet_id)
            .update({UserWallet.deleted_at: now, UserWallet.updated_at: now})
        )
