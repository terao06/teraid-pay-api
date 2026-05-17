from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce


class NonceRepository:
    def create_nonce(self, mysql_session: Session, nonce: Nonce) -> Nonce:
        """nonceを作成する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            取得した店舗情報。存在しない場合は `None`。
        """
        mysql_session.add(nonce)
        mysql_session.flush()
        return nonce

    def update_nonce(self, mysql_session: Session, nonce: Nonce) -> None:
        """更新済み nonce を保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_wallet_nonce: 更新対象の nonce エンティティ。

        Returns:
            なし。
        """
        mysql_session.add(nonce)
