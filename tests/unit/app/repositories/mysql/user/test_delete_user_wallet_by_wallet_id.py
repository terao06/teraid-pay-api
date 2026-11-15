import pytest
from sqlalchemy.orm import Session

from app.models.mysql.user_wallet import UserWallet
from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
class TestDeleteUserWalletByWalletId:
    """delete_user_wallet_by_wallet_id の動作を検証する。"""

    def test_delete_user_wallet_by_wallet_id(
        self,
        mysql_session: Session,
    ) -> None:
        """存在する wallet_id を指定した場合、対象 UserWallet の deleted_at が設定されること。"""
        repository = UserRepository()
        target_wallet_id = 315

        before = (
            mysql_session.query(UserWallet)
            .filter(UserWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_user_wallet_by_wallet_id(mysql_session, target_wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after = (
            mysql_session.query(UserWallet)
            .filter(UserWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_user_wallet_by_wallet_id_not_found(
        self,
        mysql_session: Session,
    ) -> None:
        """存在しない wallet_id を指定した場合、いずれの UserWallet も更新されないこと。"""
        repository = UserRepository()
        non_existent_wallet_id = 99999

        before_count = (
            mysql_session.query(UserWallet)
            .filter(UserWallet.deleted_at.isnot(None))
            .count()
        )

        repository.delete_user_wallet_by_wallet_id(mysql_session, non_existent_wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after_count = (
            mysql_session.query(UserWallet)
            .filter(UserWallet.deleted_at.isnot(None))
            .count()
        )
        assert after_count == before_count
