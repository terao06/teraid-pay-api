from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    StoreNotFoundException,
    WalletConflictException,
    UnauthorizedException
)
from app.core.utils.datetime import DateTimeUtil
from app.core.utils.wallet import WalletUtil
from app.models.mysql.nonce import Nonce
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_nonce import StoreNonce
from app.models.mysql.wallet import Wallet
from app.models.responses.store_wallet_response import StoreWalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import StoreWalletVerifyResponse
from app.repositories.store_repository import StoreRepository
from eth_account import Account
from eth_account.messages import encode_defunct


JST = timezone(timedelta(hours=9))


class StoreService:
    """店舗ウォレット関連処理を担当するサービス。"""

    def get_store_wallet(self, session: Session, store_id: int) -> StoreWalletResponse | None:
        """店舗 ID に紐づくウォレット情報を取得する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            店舗ウォレットのレスポンス。存在しない場合は None。
        """
        store_wallet = StoreRepository().get_store_wallet(
            session=session,
            store_id=store_id
        )

        if store_wallet is None:
            return None

        return StoreWalletResponse(
            store_wallet_id=store_wallet.store_wallet_id,
            store_id=store_wallet.store_id,
            wallet_address=store_wallet.wallet_address,
            chain_type=store_wallet.chain_type,
            network_name=store_wallet.network_name,
            is_active=store_wallet.is_active,
            verified_at=DateTimeUtil.change_datetime_to_string(store_wallet.verified_at),
            created_at=DateTimeUtil.change_datetime_to_string(store_wallet.created_at),
            updated_at=DateTimeUtil.change_datetime_to_string(store_wallet.updated_at)
        )

    def create_wallet_nonce(
        self,
        session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名に使用する nonce を生成する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        store = StoreRepository().get_store_by_id(
            session=session,
            store_id=store_id
        )
        if not store:
            raise StoreNotFoundException(f"対象の店舗は存在しません. store_id={store_id}")

        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)
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
        store_repository = StoreRepository()
        saved_nonce = store_repository.create_nonce(session=session, nonce=nonce)
        
        store_nonce = StoreNonce(
            store_id=store_id,
            nonce_id=saved_nonce.nonce_id
        )
        StoreRepository().create_store_nonce(
            session=session,
            store_nonce=store_nonce
        )
        message = WalletUtil.build_sign_message(
            store_id=store_id,
            wallet_address=wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            nonce=nonce_str,
        )

        return WalletNonceCreateResponse(
            message=message,
            nonce=nonce_str,
            expires_at=DateTimeUtil.change_datetime_to_string(expires_at)
        )

    def verify_wallet_nonce(
        self,
        session: Session,
        store_id: int,
        wallet_address: str,
        signature: str,
        chain_type: str,
        network_name: str) -> Nonce:
        """署名済み nonce を検証し、利用可能な nonce エンティティを返す。
        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 検証対象のウォレットアドレス。
            signature: 署名文字列。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
        Returns:
            検証に成功した未使用の Nonce。
        """
        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)
        repository = StoreRepository()
        store = repository.get_store_by_id(session=session, store_id=store_id)
        if store is None:
            raise StoreNotFoundException(f"対象の店舗は存在しません. store_id={store_id}")

        nonce_entity = repository.get_latest_available_nonce(
            session=session,
            store_id=store_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            expires_at=datetime.now()
        )

        if nonce_entity is None:
            raise UnauthorizedException(
                '有効なnonceが見つかりません。',
            )

        recovered_address = self._recover_address(
            message=nonce_entity.nonce,
            signature=signature,
        )

        if recovered_address.lower() != normalized_wallet_address:
            raise UnauthorizedException("認証に失敗しました。")
        return nonce_entity

    def create_store_wallet(
        self,
        session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        nonce_entity: Nonce) -> StoreWalletVerifyResponse:
        """店舗ウォレットを登録する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 登録対象のウォレットアドレス。
            signature: 署名値。
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            なし。
        """

        repository = StoreRepository()
        normalized_wallet_address = WalletUtil.normalize_wallet_address(wallet_address)

        existing_wallet = repository.get_wallet_by_store_id(
            session=session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
        )
        if existing_wallet is not None:
            raise WalletConflictException(
                f"この店舗にはすでにウォレットが登録されています。wallet_id={existing_wallet.wallet_id}")

        new_wallet = Wallet(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            verified_at=datetime.now(),
            is_active=True,
        )
        saved_wallet = repository.create_wallet(
            session=session,
            wallet=new_wallet
        )

        new_store_wallet = StoreWallet(
            store_id=store_id,
            wallet_id=saved_wallet.wallet_id
        )
        repository.create_store_wallet(
            session=session,
            store_wallet=new_store_wallet)

        nonce_entity.used_at = datetime.now()
        repository.update_store_wallet_nonce(
            session=session,
            nonce=nonce_entity
        )
        return StoreWalletVerifyResponse(
            wallet_address=new_wallet.wallet_address,
            chain_type=new_wallet.chain_type,
            network_name=new_wallet.network_name,
            is_active=bool(new_wallet.is_active),
            verified_at=DateTimeUtil.change_datetime_to_string(
                new_wallet.verified_at
            ),
        )

    @staticmethod
    def _recover_address(
        message: str,
        signature: str,
    ) -> str:
        """署名からウォレットアドレスを復元する。

        Args:
            message: 署名対象メッセージ。
            signature: 署名値。

        Returns:
            復元したウォレットアドレス。
        """
        try:
            encoded_message = encode_defunct(text=message)
            return Account.recover_message(
                encoded_message,
                signature=signature,
            )
        except Exception:
            raise UnauthorizedException("認証に失敗しました。")
