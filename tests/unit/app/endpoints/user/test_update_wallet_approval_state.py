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

        response = client.post(
            "/user/101/wallet/301/approval",
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_update_wallet_approval_state.assert_called_once()
        assert mock_update_wallet_approval_state.call_args.kwargs["wallet_id"] == 301

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
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "wallet not found",
            }
        }

    @pytest.mark.usefixtures("insert_wallets")
    def test_with_db(
        self,
        client_with_db,
        session: Session,
    ) -> None:
        wallet_id = 301
        before_wallet = session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        before_wallet.is_approval = False
        session.commit()
        session.expire_all()

        before_wallet = session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        assert before_wallet.is_approval is False

        response = client_with_db.post(
            f"/user/101/wallet/{wallet_id}/approval",
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

        session.rollback()
        session.expire_all()

        after_wallet = session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        assert after_wallet.is_approval is True
