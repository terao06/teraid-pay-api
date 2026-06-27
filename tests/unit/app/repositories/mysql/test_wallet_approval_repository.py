from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet_approval import WalletApproval
from app.repositories.mysql.wallet_approval_repository import WalletApprovalRepository


@pytest.mark.usefixtures("insert_wallets")
class TestCreateWalletApproval:
    def test_create_wallet_approval(
        self,
        mysql_session: Session,
    ) -> None:
        repository = WalletApprovalRepository()
        wallet_approval = WalletApproval(
            wallet_id=301,
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
            allowance_amount="10000000000000000000000",
            permit_deadline=datetime(2030, 1, 1, 0, 0, 0),
            approval_tx_hash="0x" + "a" * 64,
            approved_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        result = repository.create_wallet_approval(
            mysql_session=mysql_session,
            wallet_approval=wallet_approval,
        )
        mysql_session.expire_all()

        saved_wallet_approval = (
            mysql_session.query(WalletApproval)
            .filter(WalletApproval.wallet_approval_id == wallet_approval.wallet_approval_id)
            .one()
        )

        assert result is wallet_approval
        assert wallet_approval.wallet_approval_id is not None
        assert saved_wallet_approval.wallet_approval_id == wallet_approval.wallet_approval_id
        assert saved_wallet_approval.wallet_id == 301
        assert (
            saved_wallet_approval.token_contract_address
            == "0x2222222222222222222222222222222222222222"
        )
        assert (
            saved_wallet_approval.spender_address
            == "0x3333333333333333333333333333333333333333"
        )
        assert saved_wallet_approval.allowance_amount == "10000000000000000000000"
        assert saved_wallet_approval.permit_deadline == datetime(2030, 1, 1, 0, 0, 0)
        assert saved_wallet_approval.approval_tx_hash == "0x" + "a" * 64
        assert saved_wallet_approval.approved_at == datetime(2026, 4, 13, 12, 0, 0)
        assert saved_wallet_approval.created_at is not None
        assert saved_wallet_approval.updated_at is not None
        assert saved_wallet_approval.deleted_at is None
