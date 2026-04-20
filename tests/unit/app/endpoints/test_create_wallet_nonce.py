from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.store_nonce import StoreNonce
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.services.store_service import JST


class TestCreateWalletNonce:
    """create wallet nonce endpoint の unit test。"""

    @patch("app.endpoints.store.StoreController.create_wallet_nonce")
    def test_create_wallet_nonce_returns_wrapped_success(
        self,
        mock_create_wallet_nonce,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_create_wallet_nonce.return_value = WalletNonceCreateResponse(
            message="sign this message",
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

        response = client.post(
            "/store/10/wallet/nonce",
            json={
                "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                "chain_type": "ethereum",
                "network_name": "sepolia",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "nonce": "generated-nonce",
                "expires_at": "2026-04-12 12:10",
            },
        }
        mock_create_wallet_nonce.assert_called_once()
        assert mock_create_wallet_nonce.call_args.kwargs["store_id"] == 10
        request = mock_create_wallet_nonce.call_args.kwargs["request"]
        assert request.wallet_address == "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        assert request.chain_type == "ethereum"
        assert request.network_name == "sepolia"

    @patch("app.endpoints.store.StoreController.create_wallet_nonce")
    def test_create_wallet_nonce_returns_http_exception_from_controller(
        self,
        mock_create_wallet_nonce,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_create_wallet_nonce.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "store not found",
            },
        )

        response = client.post(
            "/store/10/wallet/nonce",
            json={
                "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                "chain_type": "ethereum",
                "network_name": "sepolia",
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "store not found",
            }
        }
    
    @pytest.mark.usefixtures("insert_stores")
    @patch("app.services.store_service.secrets.token_urlsafe", return_value="generated-nonce")
    def test_with_db(
        self,
        mock_token_urlsafe,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携時に nonce 作成結果と保存内容が一致することを確認する。"""
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            response = client_with_db.post(
                "/store/101/wallet/nonce",
                json={
                    "wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
                    "chain_type": "ethereum",
                    "network_name": "sepolia",
                },
            )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "nonce": "generated-nonce",
                "expires_at": "2026-04-12 12:10",
            },
        }
        mock_token_urlsafe.assert_called_once_with(32)

        saved_nonce = session.query(Nonce).one()
        saved_store_nonce = session.query(StoreNonce).one()

        assert saved_nonce.wallet_address == "0xabcdef1234567890abcdef1234567890abcdef12"
        assert saved_nonce.chain_type == "ethereum"
        assert saved_nonce.network_name == "sepolia"
        assert saved_nonce.nonce == "generated-nonce"
        expected_expires_at = (fixed_now + timedelta(minutes=10)).replace(tzinfo=None)
        assert saved_nonce.expires_at == expected_expires_at
        assert saved_nonce.used_at is None
        assert saved_store_nonce.store_id == 101
        assert saved_store_nonce.nonce_id == saved_nonce.nonce_id
