
from datetime import datetime, timedelta
import secrets

from sqlalchemy.orm import Session
from web3 import HTTPProvider, Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.core.config.blockchain import get_chain_config
from app.core.config.payment_processor import get_payment_processor_config
from app.core.config.wallet_approval import get_wallet_approval_config
from app.core.exceptions.custom_exception import (
    UnauthorizedException,
    UserNotFoundException,
    WalletConflictException,
    WalletNotApprovedException,
    WalletNotFoundException
)
from app.core.utils.datetime import JST, DateTimeUtil
from app.core.utils.logging import TeraidPayApiLog
from app.core.utils.wallet import WalletUtil
from app.models.mysql.nonce import Nonce
from app.models.mysql.user_nonce import UserNonce
from app.models.mysql.user_wallet import UserWallet
from app.models.mysql.wallet import Wallet
from app.models.mysql.wallet_approval import WalletApproval
from app.models.responses.wallet_response import WalletResponse
from app.models.responses.wallet_approval_response import WalletApprovalResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.repositories.mysql.nonce_repository import NonceRepository
from app.repositories.mysql.user_repository import UserRepository
from app.repositories.mysql.wallet_approval_repository import WalletApprovalRepository
from app.repositories.mysql.wallet_repository import WalletRepository


ERC20_ALLOWANCE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "spender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"},
        ],
        "name": "Approval",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "uint8", "name": "v", "type": "uint8"},
            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
            {"internalType": "bytes32", "name": "s", "type": "bytes32"},
        ],
        "name": "permit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def _hex_value(value) -> str:
    if hasattr(value, "hex"):
        return value.hex()
    return str(value)


def _topic_to_address(web3: Web3, topic) -> str:
    topic_hex = _hex_value(topic)
    if topic_hex.startswith("0x"):
        topic_hex = topic_hex[2:]
    return web3.to_checksum_address("0x" + topic_hex[-40:])


def _data_to_int(data) -> int:
    if isinstance(data, int):
        return data
    data_hex = _hex_value(data)
    return int(data_hex, 16)


class UserService:
    """ユーザーウォレット関連処理を担当するサービス。"""

    def get_user_wallet(self, mysql_session: Session, user_id: int) -> WalletResponse | None:
        """ユーザー ID に紐づくウォレット情報を取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。

        Returns:
            ユーザーウォレットのレスポンス。存在しない場合は None。
        """
        wallet_info = UserRepository().get_user_wallet(
            mysql_session=mysql_session,
            user_id=user_id
        )

        if wallet_info is None:
            return None

        return WalletResponse(
            wallet_id=wallet_info.wallet_id,
            wallet_address=wallet_info.wallet_address,
            chain_type=wallet_info.chain_type,
            network_name=wallet_info.network_name,
            token_symbol=wallet_info.token_symbol,
            chain_id=wallet_info.chain_id,
            is_active=wallet_info.is_active,
            is_approval=wallet_info.is_approval,
            verified_at=DateTimeUtil.change_datetime_to_string(wallet_info.verified_at),
            created_at=DateTimeUtil.change_datetime_to_string(wallet_info.created_at),
            updated_at=DateTimeUtil.change_datetime_to_string(wallet_info.updated_at)
        )

    def get_user_wallet_approval(self, mysql_session: Session, user_id: int) -> WalletApprovalResponse | None:
        wallet_info = UserRepository().get_user_wallet(
            mysql_session=mysql_session,
            user_id=user_id
        )

        if wallet_info is None:
            return None

        approval_config = get_wallet_approval_config(chain_id=wallet_info.chain_id)

        return WalletApprovalResponse(
            wallet_address=wallet_info.wallet_address,
            chain_id=wallet_info.chain_id,
            token_symbol=wallet_info.token_symbol,
            token_contract_address=approval_config.token_contract_address,
            spender_address=approval_config.spender_address,
        )
    
    def update_wallet_approval_state(
        self,
        mysql_session: Session,
        wallet_id: int,
        value: int,
        deadline: int,
        signature_recovery_id: int,
        signature_first_32_bytes: str,
        signature_second_32_bytes: str,
    ) -> None:
        wallet_repository = WalletRepository()
        wallet_info = wallet_repository.get_wallet_by_id(
            mysql_session=mysql_session,
            wallet_id=wallet_id)
        if not wallet_info:
            raise WalletNotFoundException(f"対象のウォレットは存在しません。 wallet_id={wallet_id}")

        chain_config = get_chain_config(chain_id=wallet_info.chain_id)
        approval_config = get_wallet_approval_config(chain_id=wallet_info.chain_id)
        payment_processor_config = get_payment_processor_config(chain_id=wallet_info.chain_id)
        web3 = Web3(HTTPProvider(chain_config.rpc_url))
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        token_contract_address = web3.to_checksum_address(approval_config.token_contract_address)
        wallet_address = web3.to_checksum_address(wallet_info.wallet_address)
        spender_address = web3.to_checksum_address(approval_config.spender_address)
        if not web3.eth.get_code(token_contract_address):
            raise WalletNotApprovedException("JPYCトークンアドレスにコントラクトが存在しません。")
        if not web3.eth.get_code(spender_address):
            raise WalletNotApprovedException("PaymentProcessorアドレスにコントラクトが存在しません。")

        token_contract = web3.eth.contract(
            address=token_contract_address,
            abi=ERC20_ALLOWANCE_ABI,
        )

        account = web3.eth.account.from_key(payment_processor_config.operator_private_key)
        transaction = token_contract.functions.permit(
            wallet_address,
            spender_address,
            value,
            deadline,
            signature_recovery_id,
            signature_first_32_bytes,
            signature_second_32_bytes,
        ).build_transaction({
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "chainId": wallet_info.chain_id,
        })
        signed_transaction = account.sign_transaction(transaction)
        raw_transaction = (
            signed_transaction.raw_transaction
            if hasattr(signed_transaction, "raw_transaction")
            else signed_transaction.rawTransaction
        )
        transaction_hash = web3.eth.send_raw_transaction(raw_transaction)
        transaction_hash_hex = _hex_value(transaction_hash)
        receipt = web3.eth.wait_for_transaction_receipt(transaction_hash)
        if receipt.get("status") != 1:
            raise WalletNotApprovedException("permit transactionが成功していません。")

        allowance = token_contract.functions.allowance(
            wallet_address,
            spender_address,
        ).call()
        if allowance < value:
            raise WalletNotApprovedException("PaymentProcessorへのallowanceが設定されていません。")

        wallet_info.is_approval = True

        approved_at = datetime.now(JST).replace(tzinfo=None)
        permit_deadline = datetime.fromtimestamp(deadline, JST).replace(tzinfo=None)
        wallet_approval = WalletApproval(
            wallet_id=wallet_info.wallet_id,
            token_contract_address=token_contract_address,
            spender_address=spender_address,
            allowance_amount=str(value),
            permit_deadline=permit_deadline,
            approval_tx_hash=transaction_hash_hex,
            approved_at=approved_at,
        )
        WalletApprovalRepository().create_wallet_approval(
            mysql_session=mysql_session,
            wallet_approval=wallet_approval,
        )
        wallet_repository.update_wallet(mysql_session=mysql_session, wallet=wallet_info)
        return None

    def create_wallet_nonce(
        self,
        mysql_session: Session,
        user_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名に使用する nonce を生成する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        user_repository = UserRepository()
        nonce_repository = NonceRepository()
        wallet_repository = WalletRepository()

        user = user_repository.get_user_by_id(
            mysql_session=mysql_session,
            user_id=user_id
        )
        if not user:
            raise UserNotFoundException(f"対象のユーザーは存在しません. user_id={user_id}")
        
        exist_wallet = wallet_repository.get_wallet_by_address(
            mysql_session=mysql_session,
            wallet_address=wallet_address)

        if exist_wallet is not None:
            raise WalletConflictException("このウォレットは既に使用されています。")

        normalized_wallet_address = WalletUtil.normalize_wallet_address(
            wallet_address=wallet_address)
        now = datetime.now(JST)
        expires_at = now + timedelta(minutes=10)
        nonce_str = secrets.token_urlsafe(32)
        nonce = Nonce(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            nonce=nonce_str,
            expires_at=expires_at,
        )
        saved_nonce = nonce_repository.create_nonce(mysql_session=mysql_session, nonce=nonce)

        user_nonce = UserNonce(
            user_id=user_id,
            nonce_id=saved_nonce.nonce_id
        )
        user_repository.create_user_nonce(
            mysql_session=mysql_session,
            user_nonce=user_nonce
        )

        return WalletNonceCreateResponse(
            nonce=nonce_str,
            expires_at=DateTimeUtil.change_datetime_to_string(expires_at)
        )

    def verify_wallet_nonce(
        self,
        mysql_session: Session,
        user_id: int,
        wallet_address: str,
        signature: str,
        chain_type: str,
        network_name: str) -> Nonce:
        """署名済み nonce を検証し、利用可能な nonce エンティティを返す。
        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 検証対象のウォレットアドレス。
            signature: 署名文字列。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
        Returns:
            検証に成功した未使用の Nonce。
        """
        user_repository = UserRepository()

        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)

        user = user_repository.get_user_by_id(mysql_session=mysql_session, user_id=user_id)
        if user is None:
            raise UserNotFoundException(f"対象のユーザーは存在しません. user_id={user_id}")

        user_nonce_entity = user_repository.get_latest_available_nonce(
            mysql_session=mysql_session,
            user_id=user_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            expires_at=datetime.now()
        )

        if user_nonce_entity is None:
            raise UnauthorizedException(
                '有効なnonceが見つかりません。',
            )

        recovered_address = WalletUtil.recover_address(
            message=user_nonce_entity.nonce,
            signature=signature,
        )

        if recovered_address.lower() != normalized_wallet_address:
            raise UnauthorizedException("認証に失敗しました。")
        return user_nonce_entity
    
    def create_user_wallet(
        self,
        mysql_session: Session,
        user_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        token_symbol: str,
        chain_id: int,
        nonce_entity: Nonce) -> WalletVerifyResponse:
        """店舗ウォレットを登録する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 登録対象のウォレットアドレス。
            signature: 署名値。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            WalletVerifyResponse: ウォレット検証レスポンス
        """

        user_repository = UserRepository()
        wallet_repository = WalletRepository()
        nonce_repository = NonceRepository()

        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)

        existing_wallet = user_repository.get_wallet_by_user_id(
            mysql_session=mysql_session,
            user_id=user_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )
        if existing_wallet is not None:
            TeraidPayApiLog.warning(
                f"この店舗にはすでにウォレットが登録されています。wallet_id={existing_wallet.wallet_id}")
            raise WalletConflictException(
                f"この店舗にはすでにウォレットが登録されています。wallet_id={existing_wallet.wallet_id}")

        new_wallet = Wallet(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            token_symbol=token_symbol,
            chain_id=chain_id,
            verified_at=datetime.now(),
            is_approval=False,
        )
        saved_wallet = wallet_repository.create_wallet(
            mysql_session=mysql_session,
            wallet=new_wallet
        )

        new_user_wallet = UserWallet(
            user_id=user_id,
            wallet_id=saved_wallet.wallet_id
        )
        user_repository.create_user_wallet(
            mysql_session=mysql_session,
            user_wallet=new_user_wallet)

        nonce_entity.used_at = datetime.now()
        nonce_repository.update_nonce(
            mysql_session=mysql_session,
            nonce=nonce_entity
        )
        user_repository.delete_user_nonce_by_nonce_id(
            mysql_session=mysql_session,
            nonce_id=nonce_entity.nonce_id
        )

        return WalletVerifyResponse(
            wallet_address=new_wallet.wallet_address,
            chain_type=new_wallet.chain_type,
            network_name=new_wallet.network_name,
            token_symbol=new_wallet.token_symbol,
            chain_id=new_wallet.chain_id,
            is_active=bool(new_wallet.is_active),
            is_approval=bool(new_wallet.is_approval),
            verified_at=DateTimeUtil.change_datetime_to_string(
                new_wallet.verified_at
            ),
        )

    def delete_wallet(self, mysql_session: Session, wallet_id: int) -> None:
        """ウォレットを登録から削除する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_id: 削除対象のウォレットID。

        Returns:
            なし。
        """
        WalletRepository().delete_wallet_by_wallet_id(mysql_session=mysql_session, wallet_id=wallet_id)
        UserRepository().delete_user_wallet_by_wallet_id(mysql_session=mysql_session, wallet_id=wallet_id)
