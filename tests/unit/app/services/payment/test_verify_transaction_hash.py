from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from web3.exceptions import TransactionNotFound

from app.core.exceptions.custom_exception import (
    PaymentRequestNotFoundException,
)
from app.models.mysql.payment_request import PaymentStatus
from app.models.responses.payment_verify_response import PaymentVerifyResponse
from app.services.payment_service import PaymentService


class TestVerifyTransactionHash:
    """PaymentService.verify_transaction_hash の単体テスト。"""

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_returns_confirming_when_receipt_not_found(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
    ) -> None:
        """receipt が取得できない場合は CONFIRMING に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_chain_config = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_get_chain_config.return_value = mock_chain_config
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.return_value = None

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        mock_get_chain_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_http_provider_class.assert_called_once_with(mock_chain_config.rpc_url)
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == PaymentStatus.CONFIRMING
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.CONFIRMING.value,
        )

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_returns_confirming_when_transaction_not_found(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
    ) -> None:
        """transaction がまだ RPC で見つからない場合は CONFIRMING に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_chain_config = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_get_chain_config.return_value = mock_chain_config
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.side_effect = TransactionNotFound(
            f"Transaction with hash: {transaction_hash} not found."
        )

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        mock_get_chain_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_http_provider_class.assert_called_once_with(mock_chain_config.rpc_url)
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == PaymentStatus.CONFIRMING
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.CONFIRMING.value,
        )

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_returns_tx_failed_when_receipt_status_is_zero(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
    ) -> None:
        """receipt.status が 0 の場合は TX_FAILED に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_get_chain_config.return_value = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.return_value = SimpleNamespace(status=0)

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == PaymentStatus.TX_FAILED
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.TX_FAILED.value,
        )
        mock_http_provider_class.assert_called_once()

    @pytest.mark.parametrize(
        ("is_validate", "expected_status"),
        [
            (True, PaymentStatus.PAID),
            (False, PaymentStatus.VERIFY_FAILED),
        ],
        ids=["valid-contract", "invalid-contract"],
    )
    @patch("app.services.payment_service.PaymentService._validate_payment_processed_event")
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_payment_processor_config")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_updates_status_by_contract_validation(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_get_payment_processor_config,
        mock_http_provider_class,
        mock_web3_class,
        mock_validate_payment_processed_event,
        is_validate,
        expected_status,
    ) -> None:
        """transaction の検証結果に応じて PAID/VERIFY_FAILED に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
            amount=1500,
            user_wallet_address="0x2222222222222222222222222222222222222222",
            store_wallet_address="0x3333333333333333333333333333333333333333",
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_chain_config = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_get_chain_config.return_value = mock_chain_config
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            token_contract_address="0x1111111111111111111111111111111111111111",
            payment_processor_address="0x4444444444444444444444444444444444444444",
            operator_private_key="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        mock_web3 = mock_web3_class.return_value
        receipt = SimpleNamespace(status=1)
        mock_web3.eth.get_transaction_receipt.return_value = receipt
        mock_web3.to_checksum_address.side_effect = lambda address: address
        payment_processor = mock_web3.eth.contract.return_value
        mock_validate_payment_processed_event.return_value = is_validate

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_get_payment_processor_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_web3.eth.contract.assert_called_once()
        mock_validate_payment_processed_event.assert_called_once_with(
            payment_request=target_payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == expected_status
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=expected_status.value,
        )
        mock_http_provider_class.assert_called_once()

    @pytest.mark.parametrize(
        "target_payment_request",
        [
            None,
            SimpleNamespace(
                payment_request_id=501,
                transaction_hash=None,
                chain_id=11155111,
                status=PaymentStatus.SUBMITTED,
            ),
            SimpleNamespace(
                payment_request_id=501,
                transaction_hash="",
                chain_id=11155111,
                status=PaymentStatus.SUBMITTED,
            ),
        ],
        ids=["payment-request-not-found", "transaction-hash-not-found", "transaction-hash-empty"],
    )
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_raises_when_payment_request_is_invalid(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
        target_payment_request,
    ) -> None:
        """payment または transaction_hash が取得できない場合は例外を送出する。"""
        mysql_session = Mock()
        payment_request_id = 501
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request

        with pytest.raises(PaymentRequestNotFoundException):
            PaymentService().verify_transaction_hash(
                mysql_session=mysql_session,
                payment_request_id=payment_request_id,
            )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        mock_payment_repository.update_payment_request.assert_not_called()
        mock_get_chain_config.assert_not_called()
        mock_http_provider_class.assert_not_called()
        mock_web3_class.assert_not_called()
