"""会計からの顔認証決済を開始し、送信結果と冪等性を管理する。"""

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO

from eth_utils import keccak
from PIL import Image
from sqlalchemy.orm import Session
from web3 import HTTPProvider, Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.config.blockchain import SUPPORTED_CHAIN_IDS, get_chain_config
from app.core.config.payment_processor import get_payment_processor_config

from app.core.exceptions.custom_exception import (
    DeviceCheckoutConflictException,
    DeviceCheckoutNotFoundException,
    FaceEmbeddingNotFoundException,
    InsufficientFundsError,
    PaymentRequestNotFoundException,
    UnauthorizedException,
    UserNotFoundException,
    WalletMismatchException,
    WalletNotFoundException,
    WalletNotPermittedException,
)
from app.core.exceptions.message import (
    DEVICE_CHECKOUT_CHANGED_ERROR,
    DEVICE_CHECKOUT_NOT_PAYABLE_ERROR,
    DEVICE_CHECKOUT_PROCESSING_ERROR,
)
from app.core.utils.datetime import JST
from app.helpers.device_payment_chain_helper import DevicePaymentChainHelper
from app.helpers.face_helper import FaceHelper
from app.middlewares.transaction import get_mysql_db, get_postgres_db
from app.models.mysql.device import Device
from app.models.mysql.menu_checkout import CheckoutScope, CheckoutStatus, MenuCheckout
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.responses.device_face_payment_response import DeviceFacePaymentResponse
from app.repositories.mysql.device_payment_repository import DevicePaymentRepository
from app.repositories.mysql.device_repository import DeviceRepository
from app.repositories.mysql.store_wallet_repository import StoreWalletRepository
from app.repositories.mysql.user_repository import UserRepository
from app.repositories.mysql.visit_session_repository import VisitSessionRepository
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository

logger = logging.getLogger(__name__)


# 端末決済の送信で呼び出す関数だけを定義する。
_PAYMENT_PROCESSOR_ABI = [
    {
        "inputs": [
            {"name": "paymentId", "type": "bytes32"},
            {"name": "token", "type": "address"},
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "pay",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]
_ERC20_BALANCE_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def verify_checkout_payment_on_chain(payment: PaymentRequest) -> PaymentStatus:
    """保存されたチェーンIDと送信ハッシュで端末会計の決済結果を照会する。

    Args:
        payment: DBから取得済みの端末決済試行。

    Returns:
        支払済み、失敗確定、または確認中の状態。

    Raises:
        DevicePaymentRpcUnavailable: RPC照会が失敗した場合。
        ValueError: チェーンやコントラクトの設定が不正な場合。
    """
    chain = get_chain_config(payment.chain_id)
    web3 = Web3(HTTPProvider(
        chain.rpc_url, request_kwargs={"timeout": 5}, exception_retry_configuration=None,
    ))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return DevicePaymentChainHelper.verify_checkout_payment_receipt(web3, payment)


@dataclass(frozen=True)
class _PreparedDevicePayment:
    """送信前にハッシュを確定できる署名済みトランザクション。"""

    web3: Web3
    raw_transaction: bytes

    @property
    def transaction_hash(self) -> str:
        """署名済みデータから送信前にトランザクションハッシュを計算する。

        Args:
            なし。

        Returns:
            0x付きの16進ハッシュ。
        """
        return "0x" + keccak(self.raw_transaction).hex()

    def send(self) -> str:
        """署名済みトランザクションをRPCに送信する。

        Args:
            なし。

        Returns:
            RPCが返したトランザクションハッシュ。

        Raises:
            Exception: RPC呼び出しに失敗した場合。
        """
        return self.web3.eth.send_raw_transaction(self.raw_transaction).hex()


class DevicePaymentService:
    """端末の所有権、会計の保存額、送信試行を確認して決済を開始する。

    Args:
        なし。

    Returns:
        顔認証決済開始を管理するサービス。
    """

    def start_face_payment(
        self, device_uuid: str, checkout_id: int, idempotency_key: str, content: str
    ) -> tuple[DeviceFacePaymentResponse, int]:
        """顔照合後に会計を確定し、コミット済みの決済試行を送信する。

        Args:
            device_uuid: 検証済み端末トークンのUUID。
            checkout_id: 支払う会計のID。
            idempotency_key: 同じ決済要求の再送を識別するキー。
            content: 検証済みのBase64顔画像。

        Returns:
            決済試行IDと状態、および新規・再送・送信確認中を表すHTTPステータス。

        Raises:
            UnauthorizedException: 端末が利用できない場合。
            DeviceCheckoutNotFoundException: 端末が会計を所有していない場合。
            DeviceCheckoutConflictException: 状態が決済開始を許さないか、注文や金額が変更された場合。
            Exception: 顔照合、ウォレット検証、DB、または送信前の処理に失敗した場合。
        """
        mysql = get_mysql_db()
        repository = DevicePaymentRepository()
        key_hash = sha256(idempotency_key.encode("utf-8")).digest()

        # 顔照合の前に再送を調べ、外部I/Oの間は行ロックを保持しない。
        with mysql.get_session() as session:
            device = DeviceRepository().get_device_by_uuid(session, device_uuid)
            self._require_active_device(device)
            owned = repository.get_owned_checkout(session, checkout_id, device.device_id)
            if owned is None:
                raise DeviceCheckoutNotFoundException()
            checkout, visit = owned
            existing = self._find_payment_or_check_checkout(session, device, visit, checkout, key_hash)
            if existing is not None:
                return existing, 200
            visit_id = visit.visit_session_id

        with mysql.get_session() as session, get_postgres_db().get_session() as postgres:
            user_id = self._identify_payer(session, postgres, content)

        # 注文登録と同じ順序でロックして、顔照合中の追加注文や並行送信を検知する。
        with mysql.get_session() as session, session.begin():
            device = DeviceRepository().get_device_by_uuid_for_update(session, device_uuid)
            self._require_active_device(device)
            visit = VisitSessionRepository().get_visit_session_for_update(session, device.device_id, visit_id)
            checkout = repository.get_checkout_for_update(session, checkout_id, visit_id) if visit else None
            if checkout is None:
                raise DeviceCheckoutNotFoundException()
            existing = self._find_payment_or_check_checkout(session, device, visit, checkout, key_hash)
            if existing is not None:
                return existing, 200

            payment = self._build_payment_request(
                session, device.store_id, user_id, checkout.total_amount, token_symbol=checkout.token_symbol
            )
            payment.checkout_id = checkout_id
            payment.idempotency_key_hash = key_hash
            visit.status = VisitSessionStatus.CHECKOUT_PROCESSING
            checkout.status = CheckoutStatus.PROCESSING
            repository.create_payment_request(session, payment)
            payment_request_id = payment.payment_request_id
            session.expunge(payment)

        try:
            prepared = self._prepare_payment(payment)
            transaction_hash = prepared.transaction_hash
            with mysql.get_session() as session, session.begin():
                pending = self._get_requested_payment(session, checkout_id, payment_request_id)
                pending.checkout_transaction_hash = transaction_hash
                repository.update_payment_request(session, pending)
        except Exception:
            with mysql.get_session() as session, session.begin():
                # この分岐ではRPCへの送信を一度も試みていない。
                visit = session.get(VisitSession, visit_id, with_for_update=True)
                checkout = repository.get_checkout_for_update(session, checkout_id, visit_id)
                pending = self._get_requested_payment(session, checkout_id, payment_request_id)
                pending.status = PaymentStatus.ERROR
                repository.update_payment_request(session, pending)
                checkout.status = CheckoutStatus.FAILED
                visit.status = VisitSessionStatus.ACTIVE
            raise

        try:
            sent_hash = prepared.send()
            if sent_hash.lower().removeprefix("0x") != transaction_hash[2:]:
                raise RuntimeError("RPCの返却ハッシュが署名済みハッシュと一致しません。")
            with mysql.get_session() as session, session.begin():
                pending = self._get_requested_payment(session, checkout_id, payment_request_id)
                pending.status = PaymentStatus.SUBMITTED
                repository.update_payment_request(session, pending)
        except Exception as error:
            logger.warning(
                "決済試行 %s のRPC受付状況を確認できません (%s)", payment_request_id, type(error).__name__
            )
            return DeviceFacePaymentResponse(payment_request_id=payment_request_id, status=PaymentStatus.REQUESTED), 202

        return DeviceFacePaymentResponse(payment_request_id=payment_request_id, status=PaymentStatus.SUBMITTED), 201

    @staticmethod
    def _require_active_device(device: Device | None) -> None:
        """登録済みで利用できる端末であることを確認する。"""
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

    @staticmethod
    def _get_requested_payment(session: Session, checkout_id: int, payment_request_id: int) -> PaymentRequest:
        """会計に紐づく未送信試行を取得し、存在しなければ失敗する。"""
        pending = DevicePaymentRepository().get_requested_payment(session, checkout_id, payment_request_id)
        if pending is None:
            raise PaymentRequestNotFoundException()
        return pending

    @staticmethod
    def _find_payment_or_check_checkout(
        session: Session, device: Device, visit: VisitSession, checkout: MenuCheckout, key_hash: bytes
    ) -> DeviceFacePaymentResponse | None:
        """既存の試行を返すか、新規一括決済に向けて対象注文と保存額を再照合する。"""
        existing = DevicePaymentRepository().get_checkout_payment(
            session, checkout.checkout_id, key_hash, include_processing=checkout.status == CheckoutStatus.PROCESSING
        )
        if existing is not None:
            return DeviceFacePaymentResponse(payment_request_id=existing.payment_request_id, status=existing.status)

        if visit.status == VisitSessionStatus.CHECKOUT_PROCESSING:
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_PROCESSING_ERROR)
        if checkout.scope != CheckoutScope.ALL_UNPAID:
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_CHANGED_ERROR)
        if visit.status != VisitSessionStatus.ACTIVE or checkout.status != CheckoutStatus.PENDING_CONFIRMATION:
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_NOT_PAYABLE_ERROR)

        repository = DevicePaymentRepository()
        snapshot = {
            row.menu_order_id: row.order_amount
            for row in repository.get_checkout_snapshot(session, checkout.checkout_id)
        }
        if not snapshot:
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_CHANGED_ERROR)

        orders = repository.get_unpaid_orders(session, device.store_id, visit.visit_session_id)
        current = {order.menu_order_id: order.total_amount for order in orders}
        if (
            current != snapshot
            or any(order.token_symbol != checkout.token_symbol for order in orders)
            or sum(current.values(), Decimal("0")) != checkout.total_amount
            or checkout.total_amount <= 0
        ):
            raise DeviceCheckoutConflictException(DEVICE_CHECKOUT_CHANGED_ERROR)

    @staticmethod
    def _identify_payer(mysql_session: Session, postgres_session: Session, content: str) -> int:
        """顔画像を登録済みの特徴量と照合し、支払者を特定する。"""
        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        with Image.open(BytesIO(base64.b64decode(content))) as image:
            embedding = FaceHelper.get_embedding_from_image(
                image=image.convert("RGB"), s3_client=s3_client, ssm_params=ssm_params
            )
        face = FaceEmbeddingRepository().get_nearest_face_embedding(
            postgres_session=postgres_session, embedding=embedding
        )
        if face is None or face.distance > 1.0:
            raise FaceEmbeddingNotFoundException()

        user = UserRepository().get_user_by_id(mysql_session=mysql_session, user_id=face.user_id)
        if user is None:
            raise UserNotFoundException()
        return user.user_id

    @staticmethod
    def _build_payment_request(
        mysql_session: Session, store_id: int, user_id: int, amount: Decimal, *, token_symbol: str
    ) -> PaymentRequest:
        """店舗と支払者のウォレットを検証し、会計の金額で決済試行を組み立てる。"""
        if token_symbol != "JPYC":
            raise WalletMismatchException()

        store_wallet = StoreWalletRepository().get_store_wallet(mysql_session=mysql_session, store_id=store_id)
        if store_wallet is None or not store_wallet.is_active:
            raise WalletNotFoundException()

        user_wallet = UserRepository().get_user_wallet(mysql_session=mysql_session, user_id=user_id)
        if user_wallet is None or not user_wallet.is_active:
            raise WalletNotFoundException()

        if (
            store_wallet.chain_id != user_wallet.chain_id
            or store_wallet.chain_id not in SUPPORTED_CHAIN_IDS
            or store_wallet.token_symbol != token_symbol
            or user_wallet.token_symbol != token_symbol
        ):
            raise WalletMismatchException()
        if not user_wallet.is_permitted:
            raise WalletNotPermittedException()

        return PaymentRequest(
            store_id=store_id,
            user_id=user_id,
            store_wallet_address=store_wallet.wallet_address,
            user_wallet_address=user_wallet.wallet_address,
            amount=amount,
            token_symbol=token_symbol,
            chain_id=store_wallet.chain_id,
            expires_at=datetime.now(JST) + timedelta(minutes=10),
        )

    @staticmethod
    def _prepare_payment(payment: PaymentRequest) -> _PreparedDevicePayment:
        """残高を確認し、会計ごとに固定のpaymentIdでトランザクションを署名する。"""
        chain_config = get_chain_config(chain_id=payment.chain_id)
        processor_config = get_payment_processor_config(chain_id=payment.chain_id)
        web3 = Web3(HTTPProvider(chain_config.rpc_url))
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        account = web3.eth.account.from_key(processor_config.operator_private_key)
        token_address = web3.to_checksum_address(processor_config.token_contract_address)
        payer = web3.to_checksum_address(payment.user_wallet_address)
        recipient = web3.to_checksum_address(payment.store_wallet_address)
        token = web3.eth.contract(address=token_address, abi=_ERC20_BALANCE_ABI)
        amount = int(payment.amount * Decimal(10) ** 18)
        if token.functions.balanceOf(payer).call() < amount:
            raise InsufficientFundsError()

        processor = web3.eth.contract(
            address=web3.to_checksum_address(processor_config.payment_processor_address),
            abi=_PAYMENT_PROCESSOR_ABI,
        )
        payment_id = DevicePaymentChainHelper.build_checkout_payment_id(payment.chain_id, payment.checkout_id)
        nonce = web3.eth.get_transaction_count(account.address, "pending")
        transaction = processor.functions.pay(payment_id, token_address, payer, recipient, amount).build_transaction(
            {"from": account.address, "nonce": nonce, "chainId": payment.chain_id}
        )
        signed = account.sign_transaction(transaction)
        raw_transaction = signed.raw_transaction if hasattr(signed, "raw_transaction") else signed.rawTransaction
        return _PreparedDevicePayment(web3, raw_transaction)
