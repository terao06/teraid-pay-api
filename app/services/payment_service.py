from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from web3 import Web3, HTTPProvider
from web3.exceptions import TransactionNotFound

from app.core.exceptions.custom_exception import PaymentRequestNotFoundException, WalletNotApprovedException, WalletNotFoundException
from app.core.utils.datetime import JST, DateTimeUtil
from app.core.config.blockchain import get_chain_config
from app.core.config.payment_processor import get_payment_processor_config
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.repositories.store_repository import StoreRepository
from app.repositories.user_repository import UserRepository
from app.repositories.payment_repository import PaymentRepository
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_create_response import PaymentCreateResponse
from app.models.responses.payment_verify_response import PaymentVerifyResponse


PAYMENT_PROCESSOR_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "paymentId", "type": "bytes32"},
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "pay",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "paymentId", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "token", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "to", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "address", "name": "operator", "type": "address"},
        ],
        "name": "PaymentProcessed",
        "type": "event",
    },
]


class PaymentService:
    """決済関連処理を担当するサービス。"""
    def create_payment_request(
            self,
            session: Session,
            store_id: int,
            user_id: int,
            amount: int) -> PaymentCreateResponse:
        """決済リクエスト情報を作成する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 送金先店舗のID
            user_id: 送金元ユーザーのID
            amount: 送金額

        Returns:
            PaymentCreateResponse: idを付与した決済リクエスト情報
        """
        store_repository = StoreRepository()
        user_repository = UserRepository()

        store_wallet = store_repository.get_store_wallet(
            session=session,
            store_id=store_id
        )
        if not store_wallet:
            raise WalletNotFoundException(f"店舗に紐づくウォレットが存在しません。 store_id={store_id}")

        user_wallet = user_repository.get_user_wallet(
            session=session,
            user_id=user_id
        )
        if not user_wallet:
            raise WalletNotFoundException(f"ユーザーに紐づくウォレットが存在しません。 user_id={user_id}")

        if (store_wallet.chain_id != user_wallet.chain_id) or (store_wallet.token_symbol != user_wallet.token_symbol):
            raise ValueError("値が一致しません。")

        if not user_wallet.is_approval:
            raise WalletNotApprovedException("user wallet is not approved")

        payment_repository = PaymentRepository()
        now = datetime.now(JST)
        expires_at = now + timedelta(minutes=10)
        payment_request = PaymentRequest(
            store_id=store_id,
            user_id=user_id,
            store_wallet_address=store_wallet.wallet_address,
            user_wallet_address=user_wallet.wallet_address,
            amount=amount,
            token_symbol=store_wallet.token_symbol,
            chain_id=store_wallet.chain_id,
            expires_at=expires_at
        )
        saved_payment_request = payment_repository.create_payment_request(
            session=session,
            payment_request=payment_request
        )
        return PaymentCreateResponse(
            payment_request_id=saved_payment_request.payment_request_id,
            from_wallet_address=saved_payment_request.user_wallet_address,
            to_wallet_address=saved_payment_request.store_wallet_address,
            amount=saved_payment_request.amount,
            token_symbol=saved_payment_request.token_symbol,
            chain_id=saved_payment_request.chain_id,
            expires_at=DateTimeUtil.change_datetime_to_string(saved_payment_request.expires_at)
        )

    def execute_payment(
            self,
            session: Session,
            payment_request_id: int) -> PaymentTransactionHashResponse:
        """決済リクエスト情報を作成する。

        Args:
            session: SQLAlchemy のセッション。
            payment_request_id: 送金リクエストID
            transaction_hash: 送金ハッシュ

        Returns:
            PaymentTransactionHashResponse: 送金ハッシュ結果レスポンス
        """

        payment_repository = PaymentRepository()
        target_payment_request = payment_repository.get_payment_by_id(
            session=session,
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED
        )
        if not target_payment_request:
            raise PaymentRequestNotFoundException("対象のpaymentが取得できませんでした")

        chain_config = get_chain_config(chain_id=target_payment_request.chain_id)
        payment_processor_config = get_payment_processor_config(
            chain_id=target_payment_request.chain_id)
        web3 = Web3(HTTPProvider(chain_config.rpc_url))
        account = web3.eth.account.from_key(payment_processor_config.operator_private_key)
        payment_processor = web3.eth.contract(
            address=web3.to_checksum_address(payment_processor_config.payment_processor_address),
            abi=PAYMENT_PROCESSOR_ABI,
        )
        amount = int(Decimal(str(target_payment_request.amount)) * (Decimal(10) ** 18))
        payment_id = int(payment_request_id).to_bytes(32, byteorder="big")
        transaction = payment_processor.functions.pay(
            payment_id,
            web3.to_checksum_address(payment_processor_config.token_contract_address),
            web3.to_checksum_address(target_payment_request.user_wallet_address),
            web3.to_checksum_address(target_payment_request.store_wallet_address),
            amount,
        ).build_transaction({
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "chainId": target_payment_request.chain_id,
        })
        signed_transaction = account.sign_transaction(transaction)
        raw_transaction = (
            signed_transaction.raw_transaction
            if hasattr(signed_transaction, "raw_transaction")
            else signed_transaction.rawTransaction
        )
        transaction_hash = web3.eth.send_raw_transaction(raw_transaction).hex()

        target_payment_request.transaction_hash = transaction_hash
        target_payment_request.status = PaymentStatus.SUBMITTED

        updated_payment_request = payment_repository.update_payment_request(
            session=session,
            payment_request=target_payment_request)
        return PaymentTransactionHashResponse(
            payment_request_id=updated_payment_request.payment_request_id,
            transaction_hash=updated_payment_request.transaction_hash,
        )

    def verify_transaction_hash(self, session: Session, payment_request_id: int) -> PaymentVerifyResponse:
        """決済状況を確認する。

        Args:
            session: SQLAlchemy のセッション。
            payment_request_id: 送金リクエストID。

        Returns:
            PaymentVerifyResponse: トランザクションステータスレスポンス。
        """

        payment_repository = PaymentRepository()
        target_payment_request = payment_repository.get_payment_by_id(
            session=session,
            payment_request_id=payment_request_id,
        )
        if not target_payment_request:
            raise PaymentRequestNotFoundException("対象のpaymentが取得できませんでした")

        if not target_payment_request.transaction_hash:
            raise PaymentRequestNotFoundException("対象のpaymentが取得できませんでした")

        chain_config = get_chain_config(chain_id=target_payment_request.chain_id)
        web3 = Web3(HTTPProvider(chain_config.rpc_url))

        try:
            receipt = web3.eth.get_transaction_receipt(
                transaction_hash=target_payment_request.transaction_hash)
        except TransactionNotFound:
            target_payment_request.status = PaymentStatus.CONFIRMING
            payment_repository.update_payment_request(session=session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.CONFIRMING.value
            )

        if receipt is None:
            target_payment_request.status = PaymentStatus.CONFIRMING
            payment_repository.update_payment_request(session=session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.CONFIRMING.value
            )

        if receipt.status == 0:
            target_payment_request.status = PaymentStatus.TX_FAILED
            payment_repository.update_payment_request(session=session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.TX_FAILED.value
            )
        payment_processor_config = get_payment_processor_config(
            chain_id=target_payment_request.chain_id)
        payment_processor = web3.eth.contract(
            address=web3.to_checksum_address(payment_processor_config.payment_processor_address),
            abi=PAYMENT_PROCESSOR_ABI,
        )

        is_validate = self._validate_payment_processed_event(
            payment_request=target_payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address=payment_processor_config.token_contract_address,
        )

        if not is_validate:
            target_payment_request.status = PaymentStatus.VERIFY_FAILED
            payment_repository.update_payment_request(session=session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.VERIFY_FAILED.value
            )

        target_payment_request.status = PaymentStatus.PAID
        payment_repository.update_payment_request(session=session, payment_request=target_payment_request)

        return PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.PAID.value
        )

    def _validate_payment_processed_event(
        self,
        payment_request: PaymentRequest,
        receipt,
        payment_processor,
        token_contract_address: str,
    ) -> bool:
        """取得したcontractのバリデーションを行う

        Args:
            payment_request: SQLAlchemy のセッション。
            transaction: 送金リクエストID。
            token_contract_address: 

        Returns:
            bool: バリデーション結果
        """

        events = payment_processor.events.PaymentProcessed().process_receipt(receipt)
        expected_payment_id = int(payment_request.payment_request_id).to_bytes(32, byteorder="big")
        expected_amount = int(Decimal(str(payment_request.amount)) * (Decimal(10) ** 18))

        for event in events:
            args = event.get("args", {})
            payment_id = args.get("paymentId")
            if isinstance(payment_id, str):
                payment_id = bytes.fromhex(payment_id.removeprefix("0x"))

            if bytes(payment_id) != expected_payment_id:
                continue
            if str(args.get("token")).lower() != str(token_contract_address).lower():
                continue
            if str(args.get("from")).lower() != str(payment_request.user_wallet_address).lower():
                continue
            if str(args.get("to")).lower() != str(payment_request.store_wallet_address).lower():
                continue
            if int(args.get("amount")) != expected_amount:
                continue
            return True

        return False
