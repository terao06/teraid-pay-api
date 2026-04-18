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
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_wallet_nonce import StoreWalletNonce
from app.models.responses.store_wallet_response import StoreWalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import StoreWalletVerifyResponse
from app.repositories.store_repository import StoreRepository
from eth_account import Account
from eth_account.messages import encode_defunct


JST = timezone(timedelta(hours=9))


class StoreService:
    """店舗ウォレット関連処理を担当するサービス。"""

    def get_store_wallet_list(self, session: Session, store_id: int) -> list[StoreWalletResponse]:
        """店舗 ID に紐づくウォレット一覧を取得する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            店舗ウォレットのレスポンス一覧。
        """
        store_wallets = StoreRepository().get_store_wallet_list(
            session=session,
            store_id=store_id
        )

        store_wallet_response_list = []
        for store_wallet in store_wallets:
            store_wallet_response_list.append(
                StoreWalletResponse(
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
            )
        return store_wallet_response_list

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
        nonce = secrets.token_urlsafe(32)
        store_wallet_nonce = StoreWalletNonce(
            store_id=store_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            nonce=nonce,
            expires_at=expires_at,
        )
        StoreRepository().create_store_wallet_nonce(
            session=session,
            store_wallet_nonce=store_wallet_nonce
        )
        message = WalletUtil.build_sign_message(
            store_id=store_id,
            wallet_address=wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            nonce=nonce,
        )

        return WalletNonceCreateResponse(
            message=message,
            nonce=nonce,
            expires_at=DateTimeUtil.change_datetime_to_string(expires_at)
        )
    
    def verify_wallet_nonce(
        self,
        session: Session,
        store_id: int,
        wallet_address: str,
        signature: str,
        chain_type: str,
        network_name: str) -> StoreWalletNonce:
        """署名済み nonce を検証し、利用可能な nonce エンティティを返す。
        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 検証対象のウォレットアドレス。
            signature: 署名文字列。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
        Returns:
            検証に成功した未使用の StoreWalletNonce。
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

        sign_message = WalletUtil.build_sign_message(
            store_id=store_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            nonce=nonce_entity.nonce,
        )

        recovered_address = self._recover_address(
            message=sign_message,
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
        nonce_entity: StoreWalletNonce) -> StoreWalletVerifyResponse:
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

        existing_wallet = repository.get_store_wallet_by_address(
            session=session,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
        )
        if existing_wallet is not None:
            raise WalletConflictException(
                f"このウォレットはすでに登録されています。wallet_id={existing_wallet.store_wallet_id}")

        repository.unset_primary_wallets(session=session, store_id=store_id)
        new_wallet = StoreWallet(
            store_id=store_id,
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            verified_at=datetime.now(),
            is_primary=True,
            is_active=True,
        )
        repository.create_store_wallet(
            session=session,
            store_wallet=new_wallet)
        
        nonce_entity.used_at = datetime.now()
        repository.update_store_wallet_nonce(
            session=session,
            store_wallet_nonce=nonce_entity
        )
        return StoreWalletVerifyResponse(
            wallet_address=new_wallet.wallet_address,
            chain_type=new_wallet.chain_type,
            network_name=new_wallet.network_name,
            is_primary=bool(new_wallet.is_primary),
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
