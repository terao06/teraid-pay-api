from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.responses.wallet_approval_response import WalletApprovalResponse


class TestGetUserWalletApproval:
    @patch("app.endpoints.user.UserController.get_user_wallet_approval")
    def test_get_user_wallet_approval_returns_wrapped_success(
        self,
        mock_get_user_wallet_approval,
        client,
    ) -> None:
        mock_get_user_wallet_approval.return_value = WalletApprovalResponse(
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=11155111,
            token_symbol="JPYC",
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )

        response = client.get("/user/10/wallet/approval")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_address": "0x1111111111111111111111111111111111111111",
                "chain_id": 11155111,
                "token_symbol": "JPYC",
                "token_contract_address": "0x2222222222222222222222222222222222222222",
                "spender_address": "0x3333333333333333333333333333333333333333",
            },
        }
        mock_get_user_wallet_approval.assert_called_once()
        assert mock_get_user_wallet_approval.call_args.kwargs["user_id"] == 10

    @patch("app.endpoints.user.UserController.get_user_wallet_approval")
    def test_get_user_wallet_approval_returns_http_exception_from_controller(
        self,
        mock_get_user_wallet_approval,
        client,
    ) -> None:
        mock_get_user_wallet_approval.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "wallet not found",
            },
        )

        response = client.get("/user/10/wallet/approval")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "wallet not found",
            }
        }

    @pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
    def test_with_db(self, client_with_db) -> None:
        response = client_with_db.get("/user/101/wallet/approval")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_address": "0x1111111111111111111111111111111111111111",
                "chain_id": 11155111,
                "token_symbol": "JPYC",
                "token_contract_address": "0x4444444444444444444444444444444444444444",
                "spender_address": "0x5555555555555555555555555555555555555555",
            },
        }
