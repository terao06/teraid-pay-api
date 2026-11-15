import pytest
from sqlalchemy.orm import Session

from app.models.mysql.store_wallet import StoreWallet
from app.repositories.mysql.store_wallet_repository import StoreWalletRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestDeleteStoreWalletByWalletId:
    """delete_store_wallet_by_wallet_id の動作を検証する。"""

    def test_delete_store_wallet_by_wallet_id(
        self,
        mysql_session: Session,
    ) -> None:
        """存在する wallet_id を指定した場合、対象 StoreWallet の deleted_at と updated_at が設定されること。"""
        repository = StoreWalletRepository()
        target_wallet_id = 312

        before = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_store_wallet_by_wallet_id(mysql_session, target_wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_store_wallet_by_wallet_id_not_found(
        self,
        mysql_session: Session,
    ) -> None:
        """存在しない wallet_id を指定した場合、いずれの StoreWallet も更新されないこと。"""
        repository = StoreWalletRepository()
        non_existent_wallet_id = 99999

        before_count = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.deleted_at.isnot(None))
            .count()
        )

        repository.delete_store_wallet_by_wallet_id(mysql_session, non_existent_wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after_count = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.deleted_at.isnot(None))
            .count()
        )
        assert after_count == before_count
