"""店舗管理者と失効済みトークンのデータを操作する。"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mysql.store import Store
from app.models.mysql.store_manager import StoreManager
from app.models.mysql.store_manager_revoked_token import StoreManagerRevokedToken


class StoreManagerRepository:
    """店舗管理者の検索とアクセストークンの失効管理を行う。"""

    def is_access_token_revoked(self, mysql_session: Session, jti: str) -> bool:
        """有効期限内の失効レコードが存在するかを確認する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            jti: 検証済みJWTの識別子。

        Returns:
            失効レコードが存在し、JWTの有効期限内であればTrue。
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        statement = select(StoreManagerRevokedToken.jti).where(
            StoreManagerRevokedToken.jti == jti,
            StoreManagerRevokedToken.expires_at > now,
        )
        return mysql_session.scalar(statement) is not None

    def revoke_access_token(
        self, mysql_session: Session, jti: str, store_manager_id: int, expires_at: datetime
    ) -> None:
        """指定されたJWTの失効レコードをトランザクションに追加する。

        Args:
            mysql_session: 書き込み先のSQLAlchemyセッション。
            jti: 失効するJWTの識別子。
            store_manager_id: 認証済みの店舗管理者ID。
            expires_at: JWTの有効期限（タイムゾーン情報を付けないUTC）。

        Returns:
            なし。
        """
        mysql_session.add(
            StoreManagerRevokedToken(
                jti=jti,
                store_manager_id=store_manager_id,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

    def get_store_by_id(
        self, mysql_session: Session, store_id: int
    ) -> Store | None:
        """論理削除されていない店舗をIDで取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。

        Returns:
            店舗。該当するレコードがない場合はNone。
        """
        return mysql_session.query(Store).where(
            Store.store_id == store_id,
            Store.deleted_at.is_(None),
        ).one_or_none()

    def get_store_manager_by_id(self, mysql_session: Session, store_manager_id: int) -> StoreManager | None:
        """店舗管理者IDに一致する有効な店舗管理者を取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_manager_id: 店舗管理者ID。

        Returns:
            店舗管理者。該当するレコードがない場合はNone。
        """
        return (mysql_session.query(StoreManager).join(Store, StoreManager.store_id == Store.store_id).filter(
            StoreManager.store_manager_id == store_manager_id,
            StoreManager.deleted_at.is_(None), Store.deleted_at.is_(None),
        ).one_or_none())

    def get_store_manager_by_email(self, mysql_session: Session, email: str) -> StoreManager | None:
        """メールアドレスに一致する有効な店舗管理者を取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            email: 正規化済みのメールアドレス。

        Returns:
            店舗管理者。該当するレコードがない場合はNone。
        """
        return (mysql_session.query(StoreManager).join(Store, StoreManager.store_id == Store.store_id).filter(
            StoreManager.email == email, StoreManager.deleted_at.is_(None), Store.deleted_at.is_(None),
        ).one_or_none())
