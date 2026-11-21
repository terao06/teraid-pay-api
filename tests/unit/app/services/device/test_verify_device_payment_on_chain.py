"""端末会計のチェーン照会と決済イベントの検証を確認する。"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from eth_abi import encode
from hexbytes import HexBytes
from requests.exceptions import Timeout
from web3 import Web3
from web3.exceptions import TransactionNotFound

from app.core.config.blockchain import ChainConfig
from app.core.config.payment_processor import PaymentProcessorConfig
from app.helpers.device_payment_chain_helper import DevicePaymentChainHelper, DevicePaymentRpcUnavailable
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.services.device_payment_service import verify_checkout_payment_on_chain

_CHAIN_CONFIG = "app.services.device_payment_service.get_chain_config"
_PROCESSOR_CONFIG = "app.helpers.device_payment_chain_helper.get_payment_processor_config"
_PROCESSOR = "0x" + "11" * 20
_TOKEN = "0x" + "22" * 20
_PAYER = "0x" + "33" * 20
_RECIPIENT = "0x" + "44" * 20
_HASH = "0x" + "11" * 32
_BLOCK_HASH = HexBytes("0x" + "22" * 32)


def _payment() -> PaymentRequest:
    """端末会計の照合条件を表す決済試行を作る。"""
    return PaymentRequest(
        checkout_id=9, chain_id=11155111, checkout_transaction_hash=_HASH, amount=Decimal("12.125"),
        user_wallet_address=_PAYER, store_wallet_address=_RECIPIENT,
    )


def _success_receipt(**overrides) -> dict:
    """本物のABIデコーダーで読める決済イベントを組み立てる。"""
    payment = _payment()
    event = {
        "address": _PROCESSOR,
        "payment_id": DevicePaymentChainHelper.build_checkout_payment_id(payment.chain_id, payment.checkout_id),
        "token": _TOKEN,
        "payer": _PAYER,
        "recipient": _RECIPIENT,
        "amount": 12_125_000_000_000_000_000,
    }
    event.update(overrides)
    return {"status": 1, "logs": [{
        "address": event["address"],
        "topics": [
            Web3.keccak(text="PaymentProcessed(bytes32,address,address,address,uint256,address)"),
            HexBytes(event["payment_id"]),
            HexBytes(encode(["address"], [event["token"]])),
            HexBytes(encode(["address"], [event["payer"]])),
        ],
        "data": HexBytes(encode(["address", "uint256", "address"], [
            event["recipient"], event["amount"], _PROCESSOR,
        ])),
        "logIndex": 0,
        "transactionIndex": 1,
        "transactionHash": HexBytes(_HASH),
        "blockHash": _BLOCK_HASH,
        "blockNumber": 80,
    }]}


class TestVerifyDevicePaymentOnChain:
    """成功イベントの一致、失敗を確定する条件、RPC障害を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("overrides", "expected"), [
        ({}, PaymentStatus.PAID),
        ({"address": _TOKEN}, PaymentStatus.CONFIRMING),
        ({"payment_id": bytes(32)}, PaymentStatus.CONFIRMING),
        ({"recipient": _PAYER}, PaymentStatus.CONFIRMING),
        ({"token": _PAYER}, PaymentStatus.CONFIRMING),
        ({"payer": _RECIPIENT}, PaymentStatus.CONFIRMING),
        ({"amount": 1}, PaymentStatus.CONFIRMING),
    ])
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_requires_matching_event_from_expected_contract(
        self, http_provider, web3_class, overrides: dict, expected: PaymentStatus,
    ) -> None:
        """成功レシートの発行元と全決済条件を照合する。

        Args:
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。
            overrides: 正常イベントから変更する項目。
            expected: 照合後の決済状態。

        Returns:
            なし。
        """
        web3 = web3_class.return_value
        web3.eth.contract.side_effect = Web3().eth.contract
        web3.eth.get_transaction_receipt.return_value = _success_receipt(**overrides)
        with (
            patch(_CHAIN_CONFIG, return_value=ChainConfig("https://rpc.example.invalid", _TOKEN)),
            patch(_PROCESSOR_CONFIG, return_value=PaymentProcessorConfig(_TOKEN, _PROCESSOR, "")),
        ):
            assert verify_checkout_payment_on_chain(_payment()) == expected
        web3_class.assert_called_once_with(http_provider.return_value)
        web3.eth.get_transaction_receipt.assert_called_once_with(_HASH)
        web3.eth.get_block.assert_not_called()

    @pytest.mark.parametrize(("finalized", "canonical", "processed", "expected"), [
        (79, True, False, PaymentStatus.CONFIRMING),
        (80, True, False, PaymentStatus.TX_FAILED),
        (81, False, False, PaymentStatus.CONFIRMING),
        (81, True, True, PaymentStatus.CONFIRMING),
        (81, True, False, PaymentStatus.TX_FAILED),
    ])
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_requires_finalized_failure_and_unprocessed_id(
        self, http_provider, web3_class, finalized: int, canonical: bool, processed: bool, expected: PaymentStatus,
    ) -> None:
        """確定ブロックに属する失敗と会計IDの未処理が揃った場合だけ失敗を確定する。

        Args:
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。
            finalized: チェーン上の最新確定ブロック番号。
            canonical: レシートのブロックが正規チェーンに属するか。
            processed: 確定済み状態で会計IDが処理済みか。
            expected: 照合後の決済状態。

        Returns:
            なし。
        """
        web3 = web3_class.return_value
        web3.eth.get_transaction_receipt.return_value = {"status": 0, "blockNumber": 80, "blockHash": _BLOCK_HASH}
        canonical_hash = _BLOCK_HASH if canonical else HexBytes(bytes(32))
        web3.eth.get_block.side_effect = lambda number: (
            {"number": finalized, "hash": canonical_hash} if number == "finalized" else {"hash": canonical_hash}
        )
        getter = web3.eth.contract.return_value.functions.processedPayments
        getter.return_value.call.return_value = processed
        with (
            patch(_CHAIN_CONFIG, return_value=ChainConfig("https://rpc.example.invalid", _TOKEN)),
            patch(_PROCESSOR_CONFIG, return_value=PaymentProcessorConfig(_TOKEN, _PROCESSOR, "")),
        ):
            assert verify_checkout_payment_on_chain(_payment()) == expected
        web3_class.assert_called_once_with(http_provider.return_value)
        if finalized >= 80 and canonical:
            getter.assert_called_once_with(DevicePaymentChainHelper.build_checkout_payment_id(11155111, 9))
            getter.return_value.call.assert_called_once_with(block_identifier=finalized)
        else:
            getter.assert_not_called()

    @pytest.mark.parametrize("error", [None, TransactionNotFound("missing receipt")])
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_missing_receipt_stays_confirming(self, http_provider, web3_class, error: Exception | None) -> None:
        """未検出と空の応答を決済処理中と判定する。

        Args:
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。
            error: RPCがレシート未検出を例外で返す場合の例外。

        Returns:
            なし。
        """
        web3 = web3_class.return_value
        web3.eth.get_transaction_receipt.return_value = None
        web3.eth.get_transaction_receipt.side_effect = error
        with patch(_CHAIN_CONFIG, return_value=ChainConfig("https://rpc.example.invalid", _TOKEN)):
            assert verify_checkout_payment_on_chain(_payment()) == PaymentStatus.CONFIRMING
        web3_class.assert_called_once_with(http_provider.return_value)

    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_rpc_timeout_is_reported_as_unavailable(self, http_provider, web3_class) -> None:
        """通信タイムアウトを未検出と区別して呼び出し側に伝える。

        Args:
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。

        Returns:
            なし。
        """
        web3 = web3_class.return_value
        web3.eth.get_transaction_receipt.side_effect = Timeout()
        with (
            patch(_CHAIN_CONFIG, return_value=ChainConfig("https://rpc.example.invalid", _TOKEN)),
            pytest.raises(DevicePaymentRpcUnavailable),
        ):
            verify_checkout_payment_on_chain(_payment())
        web3_class.assert_called_once_with(http_provider.return_value)
