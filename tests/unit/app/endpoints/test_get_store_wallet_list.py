from unittest.mock import patch

from fastapi import HTTPException
import pytest


class TestGetStoreWalletList:
    """get store wallet endpoint の unit test。"""

    @patch("app.endpoints.store.StoreController.get_store_wallet_list")
    def test_store_root_returns_wrapped_store_wallets(
        self,
        mock_get_store_wallet_list,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_get_store_wallet_list.return_value = [
            {
                "store_wallet_id": 1,
                "store_id": 10,
                "wallet_address": "wallet-address-1",
                "chain_type": "ETH",
                "network_name": "mainnet",
                "is_active": True,
                "verified_at": "2026-04-12 12:00",
                "created_at": "2026-04-12 12:00",
                "updated_at": "2026-04-12 12:00",
            }
        ]

        response = client.get("/store/10/wallets")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": [
                {
                    "store_wallet_id": 1,
                    "store_id": 10,
                    "wallet_address": "wallet-address-1",
                    "chain_type": "ETH",
                    "network_name": "mainnet",
                    "is_active": True,
                    "verified_at": "2026-04-12 12:00",
                    "created_at": "2026-04-12 12:00",
                    "updated_at": "2026-04-12 12:00",
                }
            ],
        }
        mock_get_store_wallet_list.assert_called_once()
        assert mock_get_store_wallet_list.call_args.kwargs["store_id"] == 10

    @patch("app.endpoints.store.StoreController.get_store_wallet_list")
    def test_store_root_returns_http_exception_from_controller(
        self,
        mock_get_store_wallet_list,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_get_store_wallet_list.side_effect = HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "server error",
            },
        )

        response = client.get("/store/10/wallets")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "server error",
            }
        }

    @pytest.mark.usefixtures("insert_stores", "insert_store_wallets")
    def test_with_db(self, client_with_db) -> None:
        """DB 連携時に店舗ウォレット一覧を取得できることを確認する。"""
        response = client_with_db.get("/store/101/wallets")

        assert response.status_code == 200

        response_data = sorted(
            response.json()["data"],
            key=lambda wallet: wallet["store_wallet_id"],
        )
        assert response.json()["status"] == "success"
        assert response_data == [
            {
                "store_wallet_id": 201,
                "store_id": 101,
                "wallet_address": "0x1111111111111111111111111111111111111111",
                "chain_type": "ETH",
                "network_name": "mainnet",
                "is_active": True,
                "verified_at": "2024-01-10 12:00",
                "created_at": "2024-01-01 09:00",
                "updated_at": "2024-01-11 10:30",
            },
            {
                "store_wallet_id": 202,
                "store_id": 101,
                "wallet_address": "0x2222222222222222222222222222222222222222",
                "chain_type": "POLYGON",
                "network_name": "amoy",
                "is_active": False,
                "verified_at": None,
                "created_at": "2024-02-01 08:00",
                "updated_at": "2024-02-05 18:45",
            },
        ]
