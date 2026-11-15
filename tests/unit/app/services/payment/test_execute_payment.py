from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    PaymentRequestNotFoundException,
)
from app.models.mysql.payment_request import PaymentStatus
from app.models.responses.payment_transaction_hash_response import (
    PaymentTransactionHashResponse,
)
from app.services.payment_service import (
    ERC20_BALANCE_ABI,
    PAYMENT_PROCESSOR_ABI,
    PaymentService,
)


class TestExecutePayment:
    """PaymentService.execute_payment の単体テスト。"""

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_payment_processor_config")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_execute_payment(self,
                             mock_payment_repository_class,
                             mock_get_chain_config,
                             mock_get_payment_processor_config,
                             mock_http_provider_class,
                             mock_web3_class) -> None:
        """REQUESTED の payment を PaymentProcessor で実行し、transaction_hash を保存することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED,
            transaction_hash=None,
            amount=1500,
            chain_id=11155111,
            user_wallet_address="0x2222222222222222222222222222222222222222",
            store_wallet_address="0x1111111111111111111111111111111111111111",
            expires_at=datetime(2026, 4, 12, 12, 10, 0),
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_payment_repository.update_payment_request.return_value = target_payment_request
        mock_get_chain_config.return_value = SimpleNamespace(rpc_url="https://example.invalid")
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            token_contract_address="0x3333333333333333333333333333333333333333",
            payment_processor_address="0x4444444444444444444444444444444444444444",
            operator_private_key="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        mock_http_provider_class.return_value = "provider"
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda address: address
        mock_account = SimpleNamespace(
            address="0x5555555555555555555555555555555555555555",
            sign_transaction=Mock(return_value=SimpleNamespace(raw_transaction=b"signed")),
        )
        mock_web3.eth.account.from_key.return_value = mock_account
        mock_web3.eth.get_transaction_count.return_value = 7
        mock_sent_hash = Mock()
        mock_sent_hash.hex.return_value = transaction_hash
        mock_web3.eth.send_raw_transaction.return_value = mock_sent_hash
        mock_payment_processor = Mock()
        mock_pay_call = Mock()
        mock_pay_call.build_transaction.return_value = {"nonce": 7}
        mock_payment_processor.functions.balanceOf.return_value.call.return_value = (
            int(Decimal(str(target_payment_request.amount)) * (Decimal(10) ** 18))
        )
        mock_payment_processor.functions.pay.return_value = mock_pay_call
        mock_web3.eth.contract.return_value = mock_payment_processor

        result = PaymentService().execute_payment(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED,
        )
        mock_get_chain_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_get_payment_processor_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_http_provider_class.assert_called_once_with("https://example.invalid")
        mock_web3_class.assert_called_once_with("provider")
        mock_web3.eth.contract.assert_any_call(
            address="0x4444444444444444444444444444444444444444",
            abi=PAYMENT_PROCESSOR_ABI,
        )
        mock_web3.eth.contract.assert_any_call(
            address="0x3333333333333333333333333333333333333333",
            abi=ERC20_BALANCE_ABI,
        )
        mock_payment_processor.functions.balanceOf.assert_called_once_with(
            target_payment_request.user_wallet_address
        )
        mock_payment_processor.functions.pay.assert_called_once_with(
            PaymentService._build_payment_id(target_payment_request),
            "0x3333333333333333333333333333333333333333",
            target_payment_request.user_wallet_address,
            target_payment_request.store_wallet_address,
            int(Decimal(str(target_payment_request.amount)) * (Decimal(10) ** 18)),
        )
        mock_pay_call.build_transaction.assert_called_once_with({
            "from": mock_account.address,
            "nonce": 7,
            "chainId": target_payment_request.chain_id,
        })
        mock_web3.eth.send_raw_transaction.assert_called_once_with(b"signed")
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.transaction_hash == transaction_hash
        assert target_payment_request.status == PaymentStatus.SUBMITTED
        assert result == PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash)

    @patch("app.services.payment_service.PaymentRepository")
    def test_execute_payment_raises_when_payment_request_not_found(
        self,
        mock_payment_repository_class,
    ) -> None:
        """REQUESTED の payment が取得できない場合は PaymentRequestNotFoundException を送出する。"""
        mysql_session = Mock()
        payment_request_id = 501
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = None

        with pytest.raises(PaymentRequestNotFoundException):
            PaymentService().execute_payment(
                mysql_session=mysql_session,
                payment_request_id=payment_request_id,
            )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED,
        )
        mock_payment_repository.update_payment_request.assert_not_called()
