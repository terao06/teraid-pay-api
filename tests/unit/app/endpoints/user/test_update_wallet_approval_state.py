from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet


class TestUpdateWalletApprovalState:
    """update wallet approval state endpoint tests."""

    @patch("app.endpoints.user.UserController.update_wallet_approval_state")
    def test_update_wallet_approval_state_returns_wrapped_success(
        self,
        mock_update_wallet_approval_state,
        client,
    ) -> None:
        mock_update_wallet_approval_state.return_value = None
        tx_hash = "0x" + "a" * 64

        response = client.post(
            "/user/101/wallet/301/approval",
            json={"tx_hash": tx_hash},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_update_wallet_approval_state.assert_called_once()
        assert mock_update_wallet_approval_state.call_args.kwargs["wallet_id"] == 301
        assert mock_update_wallet_approval_state.call_args.kwargs["tx_hash"] == tx_hash

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
            json={"tx_hash": "0x" + "a" * 64},
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
    @patch("app.services.user_service.get_wallet_approval_config")
    @patch("app.services.user_service.get_chain_config")
    def test_with_db(
        self,
        mock_get_chain_config,
        mock_get_wallet_approval_config,
        mock_web3_class,
        client_with_db,
        mysql_session: Session,
    ) -> None:
        wallet_id = 301
        tx_hash = "0x" + "a" * 64
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
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda value: value
        mock_web3.keccak.return_value = "0x" + "a" * 64
        mock_web3.eth.get_transaction_receipt.return_value = {
            "status": 1,
            "from": before_wallet.wallet_address,
            "to": "0x2222222222222222222222222222222222222222",
            "logs": [
                {
                    "address": "0x2222222222222222222222222222222222222222",
                    "topics": [
                        "0x" + "a" * 64,
                        "0x" + "0" * 24 + before_wallet.wallet_address[2:],
                        "0x" + "0" * 24 + "3333333333333333333333333333333333333333",
                    ],
                    "data": "0x1",
                }
            ],
        }
        mock_web3.eth.contract.return_value.functions.allowance.return_value.call.return_value = 1

        response = client_with_db.post(
            f"/user/101/wallet/{wallet_id}/approval",
            json={"tx_hash": tx_hash},
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
