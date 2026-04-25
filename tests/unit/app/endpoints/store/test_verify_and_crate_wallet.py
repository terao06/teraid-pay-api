from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse


class TestVerifyAndCreateWallet:
    """verify_and_create_wallet endpoint の unit test。"""

    @patch("app.endpoints.store.StoreController.verify_and_create_wallet_nonce")
    def test_verify_and_create_wallet_returns_wrapped_success(
        self,
        mock_verify_and_create_wallet_nonce,
        client,
    ) -> None:
        """controller の success レスポンスを wrapper 付きで返すことを検証する。"""
        mock_verify_and_create_wallet_nonce.return_value = WalletVerifyResponse(
            wallet_address="0xabcdef1234567890abcdef1234567890abcdef12",
            chain_type="ethereum",
            network_name="sepolia",
            is_active=True,
            verified_at="2026-04-13 12:00",
        )

        response = client.post(
            "/store/10/wallet",
            json={
                "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                "signature": "signed-message",
                "chain_type": "ethereum",
                "network_name": "sepolia",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_address": "0xabcdef1234567890abcdef1234567890abcdef12",
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "is_active": True,
                "verified_at": "2026-04-13 12:00",
            },
        }
        mock_verify_and_create_wallet_nonce.assert_called_once()
        assert mock_verify_and_create_wallet_nonce.call_args.kwargs["store_id"] == 10
        request = mock_verify_and_create_wallet_nonce.call_args.kwargs["request"]
        assert request.wallet_address == "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        assert request.signature == "signed-message"
        assert request.chain_type == "ethereum"
        assert request.network_name == "sepolia"

    @patch("app.endpoints.store.StoreController.verify_and_create_wallet_nonce")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (404, "store not found"),
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
        """controller の HTTPException をそのまま返すことを検証する。"""
        mock_verify_and_create_wallet_nonce.side_effect = HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
            },
        )

        response = client.post(
            "/store/10/wallet",
            json={
                "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                "signature": "signed-message",
                "chain_type": "ethereum",
                "network_name": "sepolia",
            },
        )

        assert response.status_code == status_code
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": message,
            }
        }

    @pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets", "insert_nonces", "insert_store_nonces")
    @patch("app.services.store_service.datetime")
    def test_with_db(
        self,
        mock_datetime,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携で nonce 検証から wallet 作成、nonce 使用済み化まで行うことを検証する。"""
        fixed_now = datetime(2026, 4, 13, 12, 0, 0)
        wallet_address = "0x7d5e89df8eaf8872895865aef6de2d9373a159de"
        mock_datetime.now.return_value = fixed_now

        response = client_with_db.post(
            "/store/101/wallet",
            json={
                "wallet_address": "0x7d5E89df8eaF8872895865AEf6De2d9373a159dE",
                "signature": "28704a0a4569f9cd6e64ef2f887948d95f9c8df3925db552db22d91703724c5679a5beb30eda5643b56cd07646e8120a784f7acb9a6f53f877ca15fa9bc4b01e1c",
                "chain_type": "ethereum",
                "network_name": "sepolia",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "wallet_address": wallet_address,
                "chain_type": "ethereum",
                "network_name": "sepolia",
                "is_active": True,
                "verified_at": "2026-04-13 12:00",
            },
        }
        created_wallet = (
            session.query(Wallet)
            .join(StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id)
            .filter(
                StoreWallet.store_id == 101,
                Wallet.wallet_address == wallet_address,
                Wallet.chain_type == "ethereum",
                Wallet.network_name == "sepolia",
                Wallet.wallet_id != 301,
            )
            .one()
        )
        assert created_wallet.is_active is True
        assert created_wallet.verified_at == fixed_now

        updated_nonce = (
            session.query(Nonce)
            .filter(Nonce.nonce_id == 7)
            .one()
        )
        assert updated_nonce.used_at == fixed_now

        existing_store_wallet = (
            session.query(StoreWallet)
            .filter(StoreWallet.store_wallet_id == 201)
            .one()
        )
        assert existing_store_wallet.store_id == 101
