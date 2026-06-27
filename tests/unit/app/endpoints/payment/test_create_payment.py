from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.services.payment_service import JST, PAYMENT_PROCESSOR_ABI, PaymentService


class TestCreatePayment:
    @patch("app.endpoints.payment.PaymentController.create_and_execute_payment")
    def test_create_payment_returns_wrapped_success(
        self,
        mock_create_and_execute_payment,
        client,
    ) -> None:
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        mock_create_and_execute_payment.return_value = PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
        )

        response = client.post(
            "/payment/request",
            json={
                "store_id": 101,
                "user_id": 201,
                "amount": 1500,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "transaction_hash": transaction_hash,
            },
        }
        mock_create_and_execute_payment.assert_called_once()
        request = mock_create_and_execute_payment.call_args.kwargs["request"]
        assert request.store_id == 101
        assert request.user_id == 201
        assert request.amount == 1500

    @patch("app.endpoints.payment.PaymentController.create_and_execute_payment")
    def test_create_payment_returns_http_exception_from_controller(
        self,
        mock_create_and_execute_payment,
        client,
    ) -> None:
        mock_create_and_execute_payment.side_effect = HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": "wallet not found",
            },
        )

        response = client.post(
            "/payment/request",
            json={
                "store_id": 101,
                "user_id": 201,
                "amount": 1500,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "wallet not found",
            }
        }

    @pytest.mark.usefixtures("insert_stores", "insert_users", "insert_wallets", "insert_store_wallets", "insert_user_wallets")
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.datetime")
    def test_with_db(
        self,
        mock_datetime,
        mock_http_provider_class,
        mock_web3_class,
        client_with_db,
        mysql_session: Session,
    ) -> None:
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)
        transaction_hash = "0xabcdef1234567890"
        mock_datetime.now.return_value = fixed_now
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda address: address
        mock_account = mock_web3.eth.account.from_key.return_value
        mock_account.address = "0x6666666666666666666666666666666666666666"
        mock_account.sign_transaction.return_value.raw_transaction = b"signed"
        mock_web3.eth.account.from_key.return_value = mock_account
        mock_web3.eth.get_transaction_count.return_value = 7
        mock_sent_hash = mock_web3.eth.send_raw_transaction.return_value
        mock_sent_hash.hex.return_value = transaction_hash
        mock_payment_processor = mock_web3.eth.contract.return_value
        mock_pay_call = mock_payment_processor.functions.pay.return_value
        mock_pay_call.build_transaction.return_value = {"nonce": 7}

        response = client_with_db.post(
            "/payment/request",
            json={
                "store_id": 101,
                "user_id": 101,
                "amount": 1500,
            },
        )

        assert response.status_code == 200
        response_json = response.json()
        payment_request_id = response_json["data"]["payment_request_id"]
        assert response.json() == {
            "status": "success",
            "data": {
                "payment_request_id": payment_request_id,
                "transaction_hash": transaction_hash,
            },
        }
        mock_http_provider_class.assert_called_once_with("https://sepolia.infura.io/v3/hogehoge")
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.account.from_key.assert_called_once_with(
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        mock_web3.eth.contract.assert_called_once_with(
            address="0x5555555555555555555555555555555555555555",
            abi=PAYMENT_PROCESSOR_ABI,
        )
        expected_payment_id = PaymentService._build_payment_id(
            SimpleNamespace(
                payment_request_id=payment_request_id,
                chain_id=11155111,
                user_wallet_address="0x1111111111111111111111111111111111111111",
                store_wallet_address="0x1111111111111111111111111111111111111111",
                amount=1500,
                expires_at=fixed_now + timedelta(minutes=10),
            )
        )
        mock_payment_processor.functions.pay.assert_called_once_with(
            expected_payment_id,
            "0x4444444444444444444444444444444444444444",
            "0x1111111111111111111111111111111111111111",
            "0x1111111111111111111111111111111111111111",
            1500000000000000000000,
        )
        mock_pay_call.build_transaction.assert_called_once_with({
            "from": mock_account.address,
            "nonce": 7,
            "chainId": 11155111,
        })
        mock_web3.eth.send_raw_transaction.assert_called_once_with(b"signed")

        mysql_session.expire_all()
        saved_payment_request = (
            mysql_session.query(PaymentRequest)
            .filter(PaymentRequest.payment_request_id == payment_request_id)
            .one()
        )
        assert saved_payment_request.payment_request_id == payment_request_id
        assert saved_payment_request.store_id == 101
        assert saved_payment_request.user_id == 101
        assert saved_payment_request.store_wallet_address == "0x1111111111111111111111111111111111111111"
        assert saved_payment_request.user_wallet_address == "0x1111111111111111111111111111111111111111"
        assert saved_payment_request.amount == Decimal("1500.000000")
        assert saved_payment_request.token_symbol == "JPYC"
        assert saved_payment_request.chain_id == 11155111
        assert saved_payment_request.status == PaymentStatus.SUBMITTED
        assert saved_payment_request.transaction_hash == transaction_hash
        assert saved_payment_request.expires_at == (fixed_now + timedelta(minutes=10)).replace(tzinfo=None)
        assert saved_payment_request.created_at is not None
        assert saved_payment_request.updated_at is not None
        assert saved_payment_request.deleted_at is None
