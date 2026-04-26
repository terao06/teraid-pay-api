from unittest.mock import patch

from fastapi import HTTPException
import pytest


class TestGetUserWallet:
    """get user wallet endpoint の unit test。"""

    @patch("app.endpoints.user.UserController.get_user_wallet")
    def test_user_root_returns_wrapped_user_wallet(
        self,
        mock_get_user_wallet,
        client,
    ) -> None:
        """controller の成功レスポンスがラップされて返ることを確認する。"""
        mock_get_user_wallet.return_value = {
            "wallet_id": 301,
            "wallet_address": "0x1111111111111111111111111111111111111111",
            "chain_type": "ETH",
            "network_name": "mainnet",
            "chain_id": 1,
            "is_active": True,
            "verified_at": "2024-01-10 12:00",
            "created_at": "2024-01-01 09:30",
            "updated_at": "2024-01-15 18:45",
        }

        response = client.get("/user/101/wallet")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_id": 301,
                "wallet_address": "0x1111111111111111111111111111111111111111",
                "chain_type": "ETH",
                "network_name": "mainnet",
                "chain_id": 1,
                "is_active": True,
                "verified_at": "2024-01-10 12:00",
                "created_at": "2024-01-01 09:30",
                "updated_at": "2024-01-15 18:45",
            },
        }
        mock_get_user_wallet.assert_called_once()
        assert mock_get_user_wallet.call_args.kwargs["user_id"] == 101

    @pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
    def test_with_db_returns_null_when_not_found(self, client_with_db) -> None:
        """DB 連携時にウォレットが存在しない場合 data が null で返ることを確認する。"""
        response = client_with_db.get("/user/103/wallet")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

    @patch("app.endpoints.user.UserController.get_user_wallet")
    def test_user_root_returns_http_exception_from_controller(
        self,
        mock_get_user_wallet,
        client,
    ) -> None:
        """controller の HTTPException がそのまま返ることを確認する。"""
        mock_get_user_wallet.side_effect = HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "server error",
            },
        )

        response = client.get("/user/101/wallet")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "server error",
            }
        }

    @pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
    def test_with_db(self, client_with_db) -> None:
        """DB 連携時に対象ユーザーのウォレットを取得できることを確認する。"""
        response = client_with_db.get("/user/101/wallet")

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"] == {
            "wallet_id": 301,
            "wallet_address": "0x1111111111111111111111111111111111111111",
            "chain_type": "ETH",
            "network_name": "mainnet",
            "chain_id": 1,
            "is_active": True,
            "verified_at": "2024-01-10 12:00",
            "created_at": "2024-01-01 09:00",
            "updated_at": "2024-01-11 10:30",
        }
