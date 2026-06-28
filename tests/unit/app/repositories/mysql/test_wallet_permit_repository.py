from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet_permit import WalletPermit
from app.repositories.mysql.wallet_permit_repository import WalletPermitRepository


@pytest.mark.usefixtures("insert_wallets")
class TestCreateWalletPermit:
    def test_create_wallet_permit(
        self,
        mysql_session: Session,
    ) -> None:
        repository = WalletPermitRepository()
        wallet_permit = WalletPermit(
            wallet_id=301,
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
            allowance_amount="10000000000000000000000",
            permit_deadline=datetime(2030, 1, 1, 0, 0, 0),
            permit_tx_hash="0x" + "a" * 64,
            permitted_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        result = repository.create_wallet_permit(
            mysql_session=mysql_session,
            wallet_permit=wallet_permit,
        )
        mysql_session.expire_all()

        saved_wallet_permit = (
            mysql_session.query(WalletPermit)
            .filter(WalletPermit.wallet_permit_id == wallet_permit.wallet_permit_id)
            .one()
        )

        assert result is wallet_permit
        assert wallet_permit.wallet_permit_id is not None
        assert saved_wallet_permit.wallet_permit_id == wallet_permit.wallet_permit_id
        assert saved_wallet_permit.wallet_id == 301
        assert (
            saved_wallet_permit.token_contract_address
            == "0x2222222222222222222222222222222222222222"
        )
        assert (
            saved_wallet_permit.spender_address
            == "0x3333333333333333333333333333333333333333"
        )
        assert saved_wallet_permit.allowance_amount == "10000000000000000000000"
        assert saved_wallet_permit.permit_deadline == datetime(2030, 1, 1, 0, 0, 0)
        assert saved_wallet_permit.permit_tx_hash == "0x" + "a" * 64
        assert saved_wallet_permit.permitted_at == datetime(2026, 4, 13, 12, 0, 0)
        assert saved_wallet_permit.created_at is not None
        assert saved_wallet_permit.updated_at is not None
        assert saved_wallet_permit.deleted_at is None
