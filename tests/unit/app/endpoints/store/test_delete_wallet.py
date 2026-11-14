from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet


class TestDeleteWallet:
    """delete_wallet エンドポイントの単体テスト。"""

    @patch("app.endpoints.store.StoreController.delete_wallet")
    def test_delete_wallet_returns_wrapped_success(
        self,
        mock_delete_wallet,
        client,
    ) -> None:
        """controller の成功結果を wrapper 付きで返すことを検証する。"""
        mock_delete_wallet.return_value = None

        response = client.delete("/store/wallet/301")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_delete_wallet.assert_called_once()
        assert mock_delete_wallet.call_args.kwargs["store_id"] == 101
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

        response = client.delete("/store/wallet/301")

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
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """DB 連携で wallet と store_wallet の論理削除が行われることを検証する。"""
        wallet_id = 311

        before_wallet = mysql_session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        before_store_wallet = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == wallet_id)
            .one()
        )
        assert before_wallet.deleted_at is None
        assert before_store_wallet.deleted_at is None
        before_wallet_updated_at = before_wallet.updated_at
        before_store_wallet_updated_at = before_store_wallet.updated_at

        response = store_client_with_db.delete(f"/store/wallet/{wallet_id}")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

        mysql_session.rollback()
        mysql_session.expire_all()

        after_wallet = mysql_session.query(Wallet).filter(Wallet.wallet_id == wallet_id).one()
        after_store_wallet = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == wallet_id)
            .one()
        )
        assert after_wallet.deleted_at is not None
        assert after_wallet.updated_at is not None
        assert after_wallet.updated_at > before_wallet_updated_at
        assert after_store_wallet.deleted_at is not None
        assert after_store_wallet.updated_at is not None
        assert after_store_wallet.updated_at > before_store_wallet_updated_at

    @pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
    def test_with_db_rejects_wallet_belonging_to_another_store(
        self,
        store_client_with_db_without_wallet_manager,
        mysql_session: Session,
    ) -> None:
        """認証管理者と異なる店舗のウォレットを削除できないことを検証する。"""
        wallet_id = 301

        response = store_client_with_db_without_wallet_manager.delete(
            f"/store/wallet/{wallet_id}"
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "ウォレット情報を取得できませんでした。",
            }
        }

        mysql_session.expire_all()
        wallet = (
            mysql_session.query(Wallet)
            .filter(Wallet.wallet_id == wallet_id)
            .one()
        )
        assert wallet.deleted_at is None
