from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce


class NonceRepository:
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

    def update_nonce(self, session: Session, nonce: Nonce) -> None:
        """更新済み nonce を保存対象としてセッションへ追加する。

        Args:
            session: SQLAlchemy のセッション。
            store_wallet_nonce: 更新対象の nonce エンティティ。

        Returns:
            なし。
        """
        session.add(nonce)