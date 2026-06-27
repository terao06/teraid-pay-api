from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet
from app.models.mysql.wallet_approval import WalletApproval


class TestUpdateWalletApprovalState:
    """update wallet approval state endpoint tests."""

    @patch("app.endpoints.user.UserController.update_wallet_approval_state")
    def test_update_wallet_approval_state_returns_wrapped_success(
        self,
        mock_update_wallet_approval_state,
        client,
    ) -> None:
        mock_update_wallet_approval_state.return_value = None
        permit = {
            "allowance_value": 1000,
            "signature_deadline": 1893456000,
            "signature_recovery_id": 27,
            "signature_first_32_bytes": "0x" + "a" * 64,
            "signature_second_32_bytes": "0x" + "b" * 64,
        }

        response = client.post(
            "/user/101/wallet/301/approval",
            json=permit,
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_update_wallet_approval_state.assert_called_once()
        assert mock_update_wallet_approval_state.call_args.kwargs["wallet_id"] == 301
        assert mock_update_wallet_approval_state.call_args.kwargs["value"] == permit["allowance_value"]
        assert mock_update_wallet_approval_state.call_args.kwargs["deadline"] == permit["signature_deadline"]
        assert mock_update_wallet_approval_state.call_args.kwargs["signature_recovery_id"] == permit["signature_recovery_id"]
        assert mock_update_wallet_approval_state.call_args.kwargs["signature_first_32_bytes"] == permit["signature_first_32_bytes"]
        assert mock_update_wallet_approval_state.call_args.kwargs["signature_second_32_bytes"] == permit["signature_second_32_bytes"]

    @patch("app.endpoints.user.UserController.update_wallet_approval_state")
    def test_update_wallet_approval_state_returns_http_exception_from_controller(
        self,
        mock_update_wallet_approval_state,
        client,
    ) -> None:
        mock_update_wallet_approval_state.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "wallet not found",
            },
        )

        response = client.post(
            "/user/101/wallet/999/approval",
            json={
                "allowance_value": 1000,
                "signature_deadline": 1893456000,
                "signature_recovery_id": 27,
                "signature_first_32_bytes": "0x" + "a" * 64,
                "signature_second_32_bytes": "0x" + "b" * 64,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "wallet not found",
            }
        }

    @pytest.mark.usefixtures("insert_wallets")
    @patch("app.services.user_service.Web3")
    @patch("app.services.user_service.get_payment_processor_config")
    @patch("app.services.user_service.get_wallet_approval_config")
    @patch("app.services.user_service.get_chain_config")
    def test_with_db(
        self,
        mock_get_chain_config,
        mock_get_wallet_approval_config,
        mock_get_payment_processor_config,
        mock_web3_class,
        client_with_db,
        mysql_session: Session,
    ) -> None:
        wallet_id = 301
        permit = {
            "allowance_value": 1000,
            "signature_deadline": 1893456000,
            "signature_recovery_id": 27,
            "signature_first_32_bytes": "0x" + "a" * 64,
            "signature_second_32_bytes": "0x" + "b" * 64,
        }
        before_wallet = mysql_session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        before_wallet.is_approval = False
        mysql_session.commit()
        mysql_session.expire_all()

        before_wallet = mysql_session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        assert before_wallet.is_approval is False
        mock_get_chain_config.return_value = type("ChainConfig", (), {"rpc_url": "https://example.test"})()
        mock_get_wallet_approval_config.return_value = type(
            "WalletApprovalConfig",
            (),
            {
                "token_contract_address": "0x2222222222222222222222222222222222222222",
                "spender_address": "0x3333333333333333333333333333333333333333",
            },
        )()
        mock_get_payment_processor_config.return_value = type(
            "PaymentProcessorConfig",
            (),
            {"operator_private_key": "0x" + "c" * 64},
        )()
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda value: value
        mock_account = mock_web3.eth.account.from_key.return_value
        mock_account.address = "0x4444444444444444444444444444444444444444"
        mock_account.sign_transaction.return_value = type("SignedTx", (), {"raw_transaction": b"raw"})()
        mock_web3.eth.get_transaction_count.return_value = 7
        mock_web3.eth.send_raw_transaction.return_value = "0x" + "d" * 64
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        mock_contract = mock_web3.eth.contract.return_value
        mock_contract.functions.permit.return_value.build_transaction.return_value = {"tx": "permit"}
        mock_contract.functions.allowance.return_value.call.return_value = 1000

        response = client_with_db.post(
            f"/user/101/wallet/{wallet_id}/approval",
            json=permit,
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

        mysql_session.rollback()
        mysql_session.expire_all()

        after_wallet = mysql_session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        assert after_wallet.is_approval is True

        saved_wallet_approval = (
            mysql_session.query(WalletApproval)
            .filter(WalletApproval.wallet_id == wallet_id)
            .one()
        )
        assert saved_wallet_approval.wallet_approval_id is not None
        assert saved_wallet_approval.wallet_id == wallet_id
        assert (
            saved_wallet_approval.token_contract_address
            == "0x2222222222222222222222222222222222222222"
        )
        assert (
            saved_wallet_approval.spender_address
            == "0x3333333333333333333333333333333333333333"
        )
        assert saved_wallet_approval.allowance_amount == "1000"
        assert saved_wallet_approval.permit_deadline == datetime(2030, 1, 1, 9, 0, 0)
        assert saved_wallet_approval.approval_tx_hash == "0x" + "d" * 64
        assert saved_wallet_approval.approved_at is not None
        assert saved_wallet_approval.created_at is not None
        assert saved_wallet_approval.updated_at is not None
        assert saved_wallet_approval.deleted_at is None
