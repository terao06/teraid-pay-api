from unittest.mock import patch

from fastapi import HTTPException
import pytest


class TestGetStoreWallet:
    """get store wallet endpoint の unit test。"""

    @patch("app.endpoints.store.StoreController.get_store_wallet")
    def test_store_root_returns_wrapped_store_wallets(
        self,
        mock_get_store_wallet,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_get_store_wallet.return_value = {
            "wallet_id": 1,
            "wallet_address": "wallet-address-1",
            "chain_type": "ETH",
            "network_name": "mainnet",
            "token_symbol": "JPYC",
            "chain_id": 1,
            "is_active": True,
            "verified_at": "2026-04-12 12:00",
            "created_at": "2026-04-12 12:00",
            "updated_at": "2026-04-12 12:00",
        }

        response = client.get("/store/10/wallet")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_id": 1,
                "wallet_address": "wallet-address-1",
                "chain_type": "ETH",
                "network_name": "mainnet",
                "token_symbol": "JPYC",
                "chain_id": 1,
                "is_active": True,
                "verified_at": "2026-04-12 12:00",
                "created_at": "2026-04-12 12:00",
                "updated_at": "2026-04-12 12:00",
            },
        }
        mock_get_store_wallet.assert_called_once()
        assert mock_get_store_wallet.call_args.kwargs["store_id"] == 10

    @patch("app.endpoints.store.StoreController.get_store_wallet")
    def test_store_root_returns_http_exception_from_controller(
        self,
        mock_get_store_wallet,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_get_store_wallet.side_effect = HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "server error",
            },
        )

        response = client.get("/store/10/wallet")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "server error",
            }
        }

    @pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
    def test_with_db(self, client_with_db) -> None:
        """DB 連携時に店舗ウォレットを取得できることを確認する。"""
        response = client_with_db.get("/store/101/wallet")

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"] == {
            "wallet_id": 301,
            "wallet_address": "0x1111111111111111111111111111111111111111",
            "chain_type": "ETH",
            "network_name": "mainnet",
            "token_symbol": "JPYC",
            "chain_id": 1,
            "is_active": True,
            "verified_at": "2024-01-10 12:00",
            "created_at": "2024-01-01 09:00",
            "updated_at": "2024-01-11 10:30",
        }

    @pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
    def test_with_db_returns_null_when_not_found(self, client_with_db) -> None:
        """DB 連携時にウォレットが存在しない場合 data が null を返すことを確認する。"""
        response = client_with_db.get("/store/103/wallet")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
