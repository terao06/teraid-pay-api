from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet
from app.repositories.mysql.wallet_repository import WalletRepository

@pytest.mark.usefixtures("insert_wallets")
class TestUpdateWallet:
    """update_wallet の動作を検証する。"""

    def test_update_wallet(
        self,
        mysql_session: Session,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = WalletRepository()
        wallet = mysql_session.query(Wallet).where(Wallet.wallet_id == 301).one()
        before_updated_at = wallet.updated_at
        verified_at = datetime(2026, 4, 13, 12, 0, 0)

        wallet.wallet_name = "updated wallet"
        wallet.is_active = False
        wallet.verified_at = verified_at

        updated_wallet = repository.update_wallet(mysql_session, wallet)
        mysql_session.flush()
        mysql_session.expire_all()

        after = mysql_session.query(Wallet).where(Wallet.wallet_id == 301).one()
        assert updated_wallet.wallet_id == 301
        assert after.wallet_name == "updated wallet"
        assert after.is_active is False
        assert after.verified_at == verified_at
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at
