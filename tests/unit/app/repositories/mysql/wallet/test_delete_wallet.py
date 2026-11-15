import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet
from app.repositories.mysql.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestDeleteWallet:
    """delete_wallet の動作を検証する。"""

    def test_delete_wallet_by_wallet_id(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = WalletRepository()
        wallet_id = 313

        before = mysql_session.query(Wallet).where(Wallet.wallet_id == wallet_id).one()
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_wallet_by_wallet_id(mysql_session, wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after = mysql_session.query(Wallet).where(Wallet.wallet_id == wallet_id).one()
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at
