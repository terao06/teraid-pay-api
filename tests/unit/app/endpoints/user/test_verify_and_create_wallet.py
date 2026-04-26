from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.user_wallet import UserWallet
from app.models.mysql.wallet import Wallet
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse


class TestVerifyAndCreateWallet:
    """verify_and_create_wallet endpoint の unit test"""

    @patch("app.endpoints.user.UserController.verify_and_create_wallet_nonce")
    def test_verify_and_create_wallet_returns_wrapped_success(
        self,
        mock_verify_and_create_wallet_nonce,
        client,
    ) -> None:
        """controller の success response が wrapper 付きで返ることを確認する"""
        mock_verify_and_create_wallet_nonce.return_value = WalletVerifyResponse(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            chain_id=11155111,
            is_active=True,
            verified_at="2026-04-13 12:00",
        )

        response = client.post(
            "/user/10/wallet",
            json={
                "wallet_address": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "signature": "signed-message",
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "chain_id": 11155111,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "chain_id": 11155111,
                "is_active": True,
                "verified_at": "2026-04-13 12:00",
            },
        }
        mock_verify_and_create_wallet_nonce.assert_called_once()
        assert mock_verify_and_create_wallet_nonce.call_args.kwargs["user_id"] == 10
        request = mock_verify_and_create_wallet_nonce.call_args.kwargs["request"]
        assert request.wallet_address == "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        assert request.signature == "signed-message"
        assert request.chain_type == "ethereum"
        assert request.network_name == "sepolia"
        assert request.chain_id == 11155111

    @patch("app.endpoints.user.UserController.verify_and_create_wallet_nonce")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (404, "user not found"),
            (401, "verification failed"),
            (409, "wallet already exists"),
        ],
    )
    def test_verify_and_create_wallet_returns_http_exception_from_controller(
        self,
        mock_verify_and_create_wallet_nonce,
        status_code,
        message,
        client,
    ) -> None:
        """controller の HTTPException がそのまま返ることを確認する"""
        mock_verify_and_create_wallet_nonce.side_effect = HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
            },
        )

        response = client.post(
            "/user/10/wallet",
            json={
                "wallet_address": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "signature": "signed-message",
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "chain_id": 11155111,
            },
        )

        assert response.status_code == status_code
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": message,
            }
        }

    @pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_nonces", "insert_user_nonces")
    @patch("app.services.user_service.datetime")
    def test_with_db(
        self,
        mock_datetime,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携で nonce 検証から wallet 作成まで行えることを確認する"""
        fixed_now = datetime(2026, 4, 13, 12, 0, 0)
        wallet_address = "0x7d5e89df8eaf8872895865aef6de2d9373a159de"
        mock_datetime.now.return_value = fixed_now

        response = client_with_db.post(
            "/user/101/wallet",
            json={
                "wallet_address": "0x7d5E89df8eaF8872895865AEf6De2d9373a159dE",
                "signature": "fcf1c4e7921a1ec72c818ed1cb5af485993be09e66fa541f0e95159c77c007fe5e335650237dbd6c24c266a96ca441f8bdf26cd52a2fc581d469790a8b11d2fe1c",
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "chain_id": 11155111,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_address": wallet_address,
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "chain_id": 11155111,
                "is_active": True,
                "verified_at": "2026-04-13 12:00",
            },
        }

        created_wallet = (
            session.query(Wallet)
            .join(UserWallet, Wallet.wallet_id == UserWallet.wallet_id)
            .filter(
                UserWallet.user_id == 101,
                Wallet.wallet_address == wallet_address,
                Wallet.chain_type == "ethereum",
                Wallet.network_name == "sepolia",
                Wallet.chain_id == 11155111,
                Wallet.wallet_id != 301,
            )
            .one()
        )
        assert created_wallet.is_active is True
        assert created_wallet.verified_at == fixed_now

        updated_nonce = (
            session.query(Nonce)
            .filter(Nonce.nonce_id == 6)
            .one()
        )
        assert updated_nonce.used_at == fixed_now

        created_user_wallet = (
            session.query(UserWallet)
            .filter(UserWallet.user_id == 101, UserWallet.wallet_id == created_wallet.wallet_id)
            .one()
        )
        assert created_user_wallet.deleted_at is None
