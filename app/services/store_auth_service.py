"""店舗管理者認証のユースケースを提供するService。"""

from sqlalchemy.orm import Session

from app.core.config.store_manager_auth import get_store_manager_auth_config
from app.core.exceptions.custom_exception import (
    StoreManagerInactiveException,
    UnauthorizedException,
)
from app.core.utils.store_manager_auth import StoreManagerAuthUtil
from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)
from app.repositories.mysql.store_manager_repository import StoreManagerRepository


class StoreAuthService:
    """店舗管理者の認証とアクセストークン発行を担当する。"""

    def login_store_manager(
        self, mysql_session: Session, email: str, password: str
    ) -> StoreManagerLoginResponse:
        """店舗管理者を認証してJWTアクセストークンを発行する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            email: 店舗管理者のメールアドレス。
            password: 店舗管理者の平文パスワード。

        Returns:
            アクセストークンと店舗管理者情報。

        Raises:
            UnauthorizedException: メールアドレスまたはパスワードが不正な場合。
            StoreManagerInactiveException: 店舗管理者アカウントが無効な場合。
        """
        store_manager = StoreManagerRepository().get_store_manager_by_email(
            mysql_session=mysql_session, email=email.strip().lower()
        )
        if store_manager is None:
            StoreManagerAuthUtil.perform_dummy_password_check(password)
            raise UnauthorizedException("店舗管理者の認証に失敗しました。")
        if not StoreManagerAuthUtil.verify_password(
            password=password, password_hash=store_manager.password_hash
        ):
            raise UnauthorizedException("店舗管理者の認証に失敗しました。")
        if not store_manager.is_active:
            raise StoreManagerInactiveException("店舗管理者アカウントは無効です。")
        auth_config = get_store_manager_auth_config()
        access_token = StoreManagerAuthUtil.create_access_token(
            store_manager=store_manager, config=auth_config
        )
        return StoreManagerLoginResponse(
            access_token=access_token,
            expires_in=auth_config.access_token_expire_seconds,
            store_manager=StoreManagerInfoResponse(
                store_manager_id=store_manager.store_manager_id,
                store_id=store_manager.store_id,
                name=store_manager.name,
                roll_id=store_manager.roll_id,
            ),
        )
