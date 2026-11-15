import pytest
from sqlalchemy.orm import Session

from app.models.mysql.user_wallet import UserWallet
from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_wallets")
class TestCreateUserWallet:
    """create_user_wallet の単体テスト。"""

    def test_create_user_wallet(
        self,
        mysql_session: Session,
    ) -> None:
        """user_wallet を保存し、flush 済みで採番済み ID を取得できることを確認する。"""
        repository = UserRepository()
        user_wallet = UserWallet(
            user_id=102,
            wallet_id=302,
        )

        result = repository.create_user_wallet(mysql_session, user_wallet)
        mysql_session.expire_all()

        saved_user_wallet = (
            mysql_session.query(UserWallet)
            .filter(UserWallet.user_wallet_id == user_wallet.user_wallet_id)
            .one()
        )

        assert result is user_wallet
        assert user_wallet.user_wallet_id is not None
        assert saved_user_wallet.user_wallet_id == user_wallet.user_wallet_id
        assert saved_user_wallet.user_id == 102
        assert saved_user_wallet.wallet_id == 302
        assert saved_user_wallet.created_at is not None
        assert saved_user_wallet.updated_at is not None
        assert saved_user_wallet.deleted_at is None
