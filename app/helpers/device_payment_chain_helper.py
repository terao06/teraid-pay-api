"""端末会計の決済IDを生成し、チェーン上で送金結果を検証する。"""

from decimal import Decimal

from eth_utils import keccak
from web3 import Web3
from web3.exceptions import TransactionNotFound, Web3Exception
from web3.logs import DISCARD
from web3.types import TxReceipt

from app.core.config.payment_processor import get_payment_processor_config
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus


_PAYMENT_RESULT_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "paymentId", "type": "bytes32"},
            {"indexed": True, "name": "token", "type": "address"},
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": False, "name": "to", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "operator", "type": "address"},
        ],
        "name": "PaymentProcessed",
        "type": "event",
    },
    {
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [{"name": "", "type": "bool"}],
        "name": "processedPayments",
        "stateMutability": "view",
        "type": "function",
    },
]


class DevicePaymentRpcUnavailable(Exception):
    """チェーンへの照会が失敗し、決済結果を判定できないことを表す。

    Args:
        なし。

    Returns:
        決済結果確認APIがHTTP 503に変換する例外。
    """


class DevicePaymentChainHelper:
    """端末会計の決済ID生成とオンチェーン結果の検証を提供する。

    Args:
        なし。

    Returns:
        端末決済のチェーン照会用ヘルパー。
    """

    @staticmethod
    def build_checkout_payment_id(chain_id: int, checkout_id: int) -> bytes:
        """送信と結果確認で共通の会計単位の決済IDを生成する。

        Args:
            chain_id: 決済を送信したチェーンID。
            checkout_id: 決済対象の会計ID。

        Returns:
            PaymentProcessorに渡す32バイトの決済ID。
        """
        return keccak(text=f"teraid-pay:checkout:v1:{chain_id}:{checkout_id}")

    @classmethod
    def verify_checkout_payment_receipt(cls, web3: Web3, payment: PaymentRequest) -> PaymentStatus:
        """保存済みの送信ハッシュで端末会計の決済結果を検証する。

        Args:
            web3: 決済に使ったチェーンの照会用Web3クライアント。
            payment: 会計と署名済みハッシュを持つ、DB参照時点の決済試行。

        Returns:
            支払済み、失敗確定、または確認中の状態。

        Raises:
            DevicePaymentRpcUnavailable: RPC照会が失敗した場合。
            ValueError: チェーンやコントラクトの設定が不正な場合。
        """
        try:
            try:
                receipt = web3.eth.get_transaction_receipt(payment.checkout_transaction_hash)
            except TransactionNotFound:
                return PaymentStatus.CONFIRMING
            if receipt is None:
                return PaymentStatus.CONFIRMING

            config = get_payment_processor_config(payment.chain_id)
            processor_address = Web3.to_checksum_address(config.payment_processor_address)
            processor = web3.eth.contract(address=processor_address, abi=_PAYMENT_RESULT_ABI)
            payment_id = cls.build_checkout_payment_id(payment.chain_id, payment.checkout_id)
            if receipt["status"] == 1:
                amount = int(payment.amount * Decimal(10) ** 18)
                expected = (
                    payment_id, config.token_contract_address.lower(),
                    payment.user_wallet_address.lower(), payment.store_wallet_address.lower(), amount,
                )
                events = processor.events.PaymentProcessed().process_receipt(receipt, errors=DISCARD)
                for event in events:
                    args = event["args"]
                    actual = (
                        args["paymentId"], args["token"].lower(),
                        args["from"].lower(), args["to"].lower(), args["amount"],
                    )
                    if event["address"].lower() == processor_address.lower() and actual == expected:
                        return PaymentStatus.PAID
            elif receipt["status"] == 0:
                finalized_number = cls._get_finalized_block_number(web3, receipt)
                if finalized_number is not None:
                    processed = processor.functions.processedPayments(payment_id).call(
                        block_identifier=finalized_number,
                    )
                    if processed is False:
                        return PaymentStatus.TX_FAILED
            return PaymentStatus.CONFIRMING
        except (OSError, Web3Exception) as error:
            raise DevicePaymentRpcUnavailable() from error

    @staticmethod
    def _get_finalized_block_number(web3: Web3, receipt: TxReceipt) -> int | None:
        """レシートが確定済みチェーンに属する場合に、その確定先端のブロック番号を返す。"""
        finalized = web3.eth.get_block("finalized")
        receipt_number = receipt["blockNumber"]
        finalized_number = finalized["number"]
        if receipt_number > finalized_number:
            return None
        canonical = finalized if receipt_number == finalized_number else web3.eth.get_block(receipt_number)
        return finalized_number if canonical["hash"] == receipt["blockHash"] else None
