from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.user_nonce import UserNonce
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.services.user_service import JST


class TestCreateWalletNonce:
    """create wallet nonce endpoint の unit test。"""

    @patch("app.endpoints.user.UserController.create_wallet_nonce")
    def test_create_wallet_nonce_returns_wrapped_success(
        self,
        mock_create_wallet_nonce,
        client,
    ) -> None:
        """controller の成功レスポンスが success ラップで返ることを確認する。"""
        mock_create_wallet_nonce.return_value = WalletNonceCreateResponse(
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

        response = client.post(
            "/user/10/wallet/nonce",
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
        assert mock_create_wallet_nonce.call_args.kwargs["user_id"] == 10
        request = mock_create_wallet_nonce.call_args.kwargs["request"]
        assert request.wallet_address == "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        assert request.chain_type == "ethereum"
        assert request.network_name == "sepolia"

    @patch("app.endpoints.user.UserController.create_wallet_nonce")
    def test_create_wallet_nonce_returns_http_exception_from_controller(
        self,
        mock_create_wallet_nonce,
        client,
    ) -> None:
        """controller の HTTPException がそのまま返ることを確認する。"""
        mock_create_wallet_nonce.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "user not found",
            },
        )

        response = client.post(
            "/user/10/wallet/nonce",
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
                "message": "user not found",
            }
        }

    @pytest.mark.usefixtures("insert_users")
    @patch("app.services.user_service.secrets.token_urlsafe", return_value="generated-nonce")
    def test_with_db(
        self,
        mock_token_urlsafe,
        client_with_db,
        session: Session,
    ) -> None:
        """DB 連携時に nonce と user_nonce が保存されることを確認する。"""
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        with patch("app.services.user_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            response = client_with_db.post(
                "/user/101/wallet/nonce",
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
        saved_user_nonce = session.query(UserNonce).one()

        assert saved_nonce.wallet_address == "0xabcdef1234567890abcdef1234567890abcdef12"
        assert saved_nonce.chain_type == "ethereum"
        assert saved_nonce.network_name == "sepolia"
        assert saved_nonce.nonce == "generated-nonce"
        expected_expires_at = (fixed_now + timedelta(minutes=10)).replace(tzinfo=None)
        assert saved_nonce.expires_at == expected_expires_at
        assert saved_nonce.used_at is None
        assert saved_user_nonce.user_id == 101
        assert saved_user_nonce.nonce_id == saved_nonce.nonce_id
        assert saved_user_nonce.created_at is not None
        assert saved_user_nonce.updated_at is not None
        assert saved_user_nonce.deleted_at is None
