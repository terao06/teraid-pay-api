
from datetime import datetime, timedelta
import secrets

from sqlalchemy.orm import Session
from app.core.exceptions.custom_exception import UnauthorizedException, UserNotFoundException, WalletConflictException
from app.core.utils.datetime import JST, DateTimeUtil
from app.core.utils.logging import TeraidPayApiLog
from app.core.utils.wallet import WalletUtil
from app.models.mysql.nonce import Nonce
from app.models.mysql.user_nonce import UserNonce
from app.models.mysql.user_wallet import UserWallet
from app.models.mysql.wallet import Wallet
from app.models.responses.wallet_response import WalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.repositories.nonce_repository import NonceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wallet_repository import WalletRepository


class UserService:
    """ユーザーウォレット関連処理を担当するサービス。"""

    def get_user_wallet(self, session: Session, user_id: int) -> WalletResponse | None:
        """ユーザー ID に紐づくウォレット情報を取得する。

        Args:
            session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。

        Returns:
            ユーザーウォレットのレスポンス。存在しない場合は None。
        """
        wallet_info = UserRepository().get_user_wallet(
            session=session,
            user_id=user_id
        )

        if wallet_info is None:
            return None

        return WalletResponse(
            wallet_id=wallet_info.wallet_id,
            wallet_address=wallet_info.wallet_address,
            chain_type=wallet_info.chain_type,
            network_name=wallet_info.network_name,
            chain_id=wallet_info.chain_id,
            is_active=wallet_info.is_active,
            verified_at=DateTimeUtil.change_datetime_to_string(wallet_info.verified_at),
            created_at=DateTimeUtil.change_datetime_to_string(wallet_info.created_at),
            updated_at=DateTimeUtil.change_datetime_to_string(wallet_info.updated_at)
        )

    def create_wallet_nonce(
        self,
        session: Session,
        user_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名に使用する nonce を生成する。

        Args:
            session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        user = UserRepository().get_user_by_id(
            session=session,
            user_id=user_id
        )
        if not user:
            raise UserNotFoundException(f"対象のユーザーは存在しません. user_id={user_id}")

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
        saved_nonce = NonceRepository().create_nonce(session=session, nonce=nonce)
        
        user_nonce = UserNonce(
            user_id=user_id,
            nonce_id=saved_nonce.nonce_id
        )
        UserRepository().create_user_nonce(
            session=session,
            user_nonce=user_nonce
        )

        return WalletNonceCreateResponse(
            nonce=nonce_str,
            expires_at=DateTimeUtil.change_datetime_to_string(expires_at)
        )

    def verify_wallet_nonce(
        self,
        session: Session,
        user_id: int,
        wallet_address: str,
        signature: str,
        chain_type: str,
        network_name: str) -> Nonce:
        """署名済み nonce を検証し、利用可能な nonce エンティティを返す。
        Args:
            session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 検証対象のウォレットアドレス。
            signature: 署名文字列。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
        Returns:
            検証に成功した未使用の Nonce。
        """
        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)
        repository = UserRepository()
        store = repository.get_user_by_id(session=session, user_id=user_id)
        if store is None:
            raise UserNotFoundException(f"対象のユーザーは存在しません. user_id={user_id}")

        stor_nonce_entity = repository.get_latest_available_nonce(
            session=session,
            user_id=user_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            expires_at=datetime.now()
        )

        if stor_nonce_entity is None:
            raise UnauthorizedException(
                '有効なnonceが見つかりません。',
            )

        recovered_address = WalletUtil.recover_address(
            message=stor_nonce_entity.nonce,
            signature=signature,
        )

        if recovered_address.lower() != normalized_wallet_address:
            raise UnauthorizedException("認証に失敗しました。")
        return stor_nonce_entity
    
    def create_store_wallet(
        self,
        session: Session,
        user_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        chain_id: int,
        nonce_entity: Nonce) -> WalletVerifyResponse:
        """店舗ウォレットを登録する。

        Args:
            session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            wallet_address: 登録対象のウォレットアドレス。
            signature: 署名値。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            WalletVerifyResponse: ウォレット検証レスポンス
        """

        user_repository = UserRepository()
        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)

        existing_wallet = user_repository.get_wallet_by_user_id(
            session=session,
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
            chain_id=chain_id,
            verified_at=datetime.now(),
            is_active=True,
        )
        saved_wallet = WalletRepository().create_wallet(
            session=session,
            wallet=new_wallet
        )

        new_store_wallet = UserWallet(
            user_id=user_id,
            wallet_id=saved_wallet.wallet_id
        )
        user_repository.create_user_wallet(
            session=session,
            user_wallet=new_store_wallet)

        nonce_entity.used_at = datetime.now()
        NonceRepository().update_nonce(
            session=session,
            nonce=nonce_entity
        )
        user_repository.delete_user_nonce_by_nonce_id(
            session=session,
            nonce_id=nonce_entity.nonce_id
        )

        return WalletVerifyResponse(
            wallet_address=new_wallet.wallet_address,
            chain_type=new_wallet.chain_type,
            network_name=new_wallet.network_name,
            chain_id=new_wallet.chain_id,
            is_active=bool(new_wallet.is_active),
            verified_at=DateTimeUtil.change_datetime_to_string(
                new_wallet.verified_at
            ),
        )
    
    def delete_wallet(self, session: Session, wallet_id: int) -> None:
        """ウォレットを登録から削除する。

        Args:
            session: SQLAlchemy のセッション。
            wallet_id: 削除対象のウォレットID。

        Returns:
            なし。
        """
        WalletRepository().delete_wallet_by_wallet_id(session=session, wallet_id=wallet_id)
        UserRepository().delete_user_wallet_by_wallet_id(session=session, wallet_id=wallet_id)
