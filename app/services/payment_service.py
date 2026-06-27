import base64
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Protocol

from PIL import Image
from sqlalchemy.orm import Session
from web3 import Web3, HTTPProvider
from web3.contract import Contract
from web3.exceptions import TransactionNotFound
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import TxReceipt

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import (
    FaceEmbeddingNotFoundException,
    PaymentRequestNotFoundException,
    UserNotFoundException,
    WalletNotApprovedException,
    WalletNotFoundException
)
from app.core.utils.datetime import JST
from app.core.config.blockchain import get_chain_config
from app.core.config.payment_processor import get_payment_processor_config
from app.core.utils.logging import TeraidPayApiLog
from app.helpers.face_helper import FaceHelper
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.repositories.mysql.store_repository import StoreRepository
from app.repositories.mysql.user_repository import UserRepository
from app.repositories.mysql.payment_repository import PaymentRepository
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_verify_response import PaymentVerifyResponse
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


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


class PaymentIdSource(Protocol):
    payment_request_id: int
    chain_id: int
    user_wallet_address: str
    store_wallet_address: str
    amount: Decimal | int | str
    expires_at: datetime | str


class PaymentService:
    """決済関連処理を担当するサービス。"""
    def get_user_id_from_face_image(
            self,
            mysql_session: Session,
            postgres_session: Session,
            content: str,
            threshold: float = 0.7) -> int:
        """顔画像からuser_idを取得する

        Args:
            mysql_session: SQLAlchemy のセッション。
            postgres_session: SQLAlchemy のセッション。
            store_id: 送金先店舗のID
            content: 送金元ユーザーのID

        Returns:
            int: ユーザーID。
        """
        self.ssm_params = SsmClient()
        self.s3_client = S3Client(s3_endpoint=self.ssm_params.s3_endpoint)

        image_bytes = base64.b64decode(content)
        target_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        embedding = FaceHelper.get_embedding_from_image(
            image=target_image,
            s3_client=self.s3_client,
            ssm_params=self.ssm_params,
        )
        face_info = FaceEmbeddingRepository().get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=threshold,
        )
        if face_info is None:
            TeraidPayApiLog.warning("対象の顔画像は登録されていません。")
            raise FaceEmbeddingNotFoundException("顔画像が登録されていません。")

        user = UserRepository().get_user_by_id(
            mysql_session=mysql_session,
            user_id=face_info.user_id
        )
        if user is None:
            TeraidPayApiLog.warning(f"対象のユーザーは存在しません。 user_id: {face_info.user_id}")
            raise UserNotFoundException("ユーザーが存在しません。")
        return user.user_id

    def create_payment_request(
            self,
            mysql_session: Session,
            store_id: int,
            user_id: int,
            amount: int) -> int:
        """決済リクエスト情報を作成する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 送金先店舗のID
            user_id: 送金元ユーザーのID
            amount: 送金額

        Returns:
            int: 作成した決済リクエスト ID。
        """
        store_repository = StoreRepository()
        user_repository = UserRepository()

        store_wallet = store_repository.get_store_wallet(
            mysql_session=mysql_session,
            store_id=store_id
        )
        if not store_wallet:
            raise WalletNotFoundException(f"店舗に紐づくウォレットが存在しません。 store_id={store_id}")

        user_wallet = user_repository.get_user_wallet(
            mysql_session=mysql_session,
            user_id=user_id
        )
        if not user_wallet:
            raise WalletNotFoundException(f"ユーザーに紐づくウォレットが存在しません。 user_id={user_id}")

        if (store_wallet.chain_id != user_wallet.chain_id) or (store_wallet.token_symbol != user_wallet.token_symbol):
            raise ValueError("値が一致しません。")

        if not user_wallet.is_approval:
            raise WalletNotApprovedException("対象のウォレットは利用許可がされていません。")

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
            mysql_session=mysql_session,
            payment_request=payment_request
        )
        return saved_payment_request.payment_request_id

    def execute_payment(
            self,
            mysql_session: Session,
            payment_request_id: int) -> PaymentTransactionHashResponse:
        """決済リクエスト情報を作成する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            payment_request_id: 送金リクエストID
            transaction_hash: 送金ハッシュ

        Returns:
            PaymentTransactionHashResponse: 送金ハッシュ結果レスポンス
        """

        payment_repository = PaymentRepository()

        # 未送信の決済リクエストを取得し、送信済みや存在しないリクエストを除外する。
        target_payment_request = payment_repository.get_payment_by_id(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED
        )
        if not target_payment_request:
            raise PaymentRequestNotFoundException("対象のpaymentが取得できませんでした")

        # 対象チェーンの RPC と PaymentProcessor コントラクト情報を読み込む。
        chain_config = get_chain_config(chain_id=target_payment_request.chain_id)
        payment_processor_config = get_payment_processor_config(
            chain_id=target_payment_request.chain_id)
        web3 = Web3(HTTPProvider(chain_config.rpc_url))
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # オペレーター秘密鍵から送信者アカウントを復元し、コントラクト操作用のインスタンスを作成する。
        account = web3.eth.account.from_key(payment_processor_config.operator_private_key)
        payment_processor = web3.eth.contract(
            address=web3.to_checksum_address(payment_processor_config.payment_processor_address),
            abi=PAYMENT_PROCESSOR_ABI,
        )

        # コントラクトに渡す金額と paymentId を、オンチェーン形式に変換する。
        amount = int(Decimal(str(target_payment_request.amount)) * (Decimal(10) ** 18))
        payment_id = self._build_payment_id(target_payment_request)

        # PaymentProcessor.pay を呼び出すトランザクションを組み立てる。
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

        # オペレーター鍵で署名し、署名済みトランザクションをブロックチェーンへ送信する。
        signed_transaction = account.sign_transaction(transaction)
        raw_transaction = (
            signed_transaction.raw_transaction
            if hasattr(signed_transaction, "raw_transaction")
            else signed_transaction.rawTransaction
        )
        transaction_hash = web3.eth.send_raw_transaction(raw_transaction).hex()

        # 送信したトランザクションハッシュを保存し、決済ステータスを送信済みに更新する。
        target_payment_request.transaction_hash = transaction_hash
        target_payment_request.status = PaymentStatus.SUBMITTED

        updated_payment_request = payment_repository.update_payment_request(
            mysql_session=mysql_session,
            payment_request=target_payment_request)
        return PaymentTransactionHashResponse(
            payment_request_id=updated_payment_request.payment_request_id,
            transaction_hash=updated_payment_request.transaction_hash,
        )

    def verify_transaction_hash(self, mysql_session: Session, payment_request_id: int) -> PaymentVerifyResponse:
        """決済状況を確認する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            payment_request_id: 送金リクエストID。

        Returns:
            PaymentVerifyResponse: トランザクションステータスレスポンス。
        """

        payment_repository = PaymentRepository()
        target_payment_request = payment_repository.get_payment_by_id(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        if not target_payment_request:
            raise PaymentRequestNotFoundException("対象のpaymentが取得できませんでした")

        if not target_payment_request.transaction_hash:
            raise PaymentRequestNotFoundException("対象のpaymentが取得できませんでした")

        chain_config = get_chain_config(chain_id=target_payment_request.chain_id)
        web3 = Web3(HTTPProvider(chain_config.rpc_url))
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        try:
            receipt = web3.eth.get_transaction_receipt(
                transaction_hash=target_payment_request.transaction_hash)
        except TransactionNotFound:
            target_payment_request.status = PaymentStatus.CONFIRMING
            payment_repository.update_payment_request(mysql_session=mysql_session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.CONFIRMING.value
            )

        if receipt is None:
            target_payment_request.status = PaymentStatus.CONFIRMING
            payment_repository.update_payment_request(mysql_session=mysql_session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.CONFIRMING.value
            )

        if receipt.status == 0:
            target_payment_request.status = PaymentStatus.TX_FAILED
            payment_repository.update_payment_request(mysql_session=mysql_session, payment_request=target_payment_request)

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
            payment_repository.update_payment_request(mysql_session=mysql_session, payment_request=target_payment_request)

            return PaymentVerifyResponse(
                payment_request_id=payment_request_id,
                status=PaymentStatus.VERIFY_FAILED.value
            )

        target_payment_request.status = PaymentStatus.PAID
        payment_repository.update_payment_request(mysql_session=mysql_session, payment_request=target_payment_request)

        return PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.PAID.value
        )

    def _validate_payment_processed_event(
        self,
        payment_request: PaymentRequest,
        receipt: TxReceipt,
        payment_processor: Contract,
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
        expected_payment_ids = {
            self._build_payment_id(payment_request),
            int(payment_request.payment_request_id).to_bytes(32, byteorder="big"),
        }
        expected_amount = int(Decimal(str(payment_request.amount)) * (Decimal(10) ** 18))

        for event in events:
            args = event.get("args", {})
            payment_id = args.get("paymentId")
            if isinstance(payment_id, str):
                payment_id = bytes.fromhex(payment_id.removeprefix("0x"))

            if bytes(payment_id) not in expected_payment_ids:
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

    @staticmethod
    def _build_payment_id(payment_request: PaymentIdSource) -> bytes:
        """PaymentProcessor に渡す paymentId を作成する。

        Args:
            payment_request: 決済リクエスト情報。

        Returns:
            bytes: PaymentProcessor の paymentId として使用する bytes32 値。
        """
        expires_at = payment_request.expires_at
        expires_at_text = (
            expires_at.isoformat()
            if hasattr(expires_at, "isoformat")
            else str(expires_at)
        )
        amount = int(Decimal(str(payment_request.amount)) * (Decimal(10) ** 18))
        source = (
            f"teraid-pay:v1:"
            f"{payment_request.chain_id}:"
            f"{payment_request.payment_request_id}:"
            f"{payment_request.user_wallet_address.lower()}:"
            f"{payment_request.store_wallet_address.lower()}:"
            f"{amount}:"
            f"{expires_at_text}"
        )
        return Web3.keccak(text=source)
