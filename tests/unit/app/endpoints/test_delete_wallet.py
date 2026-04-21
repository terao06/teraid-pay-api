from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet


class TestDeleteWallet:
    """delete_wallet endpoint の unit test。"""

    @patch("app.endpoints.store.StoreController.delete_wallet")
    def test_delete_wallet_returns_wrapped_success(
        self,
        mock_delete_wallet,
        client,
    ) -> None:
        """controller の成功結果を wrapper 付きで返すことを検証する。"""
        mock_delete_wallet.return_value = None

        response = client.delete("/store/10/wallet/301")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_delete_wallet.assert_called_once()
        assert mock_delete_wallet.call_args.kwargs["wallet_id"] == 301

    @patch("app.endpoints.store.StoreController.delete_wallet")
    def test_delete_wallet_returns_http_exception_from_controller(
        self,
        mock_delete_wallet,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを検証する。"""
        mock_delete_wallet.side_effect = HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "server error",
            },
        )

        response = client.delete("/store/10/wallet/301")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "server error",
            }
        }

    @pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
    def test_with_db(
        self,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携で wallet と store_wallet の論理削除が行われることを検証する。"""
        wallet_id = 301

        before_wallet = session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        before_store_wallet = (
            session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == wallet_id)
            .one()
        )
        assert before_wallet.deleted_at is None
        assert before_store_wallet.deleted_at is None
        before_wallet_updated_at = before_wallet.updated_at
        before_store_wallet_updated_at = before_store_wallet.updated_at

        response = client_with_db.delete(f"/store/101/wallet/{wallet_id}")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

        session.flush()
        session.expire_all()

        after_wallet = session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        after_store_wallet = (
            session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == wallet_id)
            .one()
        )
        assert after_wallet.deleted_at is not None
        assert after_wallet.updated_at is not None
        assert after_wallet.updated_at > before_wallet_updated_at
        assert after_store_wallet.deleted_at is not None
        assert after_store_wallet.updated_at is not None
        assert after_store_wallet.updated_at > before_store_wallet_updated_at
