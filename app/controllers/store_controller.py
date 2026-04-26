from sqlalchemy.orm import Session

from app.middlewares.transaction import transaction
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.services.store_service import StoreService
from app.models.responses.wallet_response import WalletResponse
from app.core.exceptions.message import SERVER_ERROR, STORE_NOT_FOUND_ERROR, VERIFY_ERROR, WALLET_CONFLICT_ERROR
from app.core.exceptions.custom_exception import CustomHttpException, StoreNotFoundException, UnauthorizedException, WalletConflictException


class StoreController:
    """店舗ウォレット取得 API のリクエストを処理するコントローラーです。"""

    @transaction
    def get_store_wallet(self, session: Session, store_id: int) -> WalletResponse | None:
        """リクエスト条件に一致する店舗ウォレットを取得します。

        Args:
            session: SQLAlchemy のセッションです。
            store_id: 取得対象の店舗 IDです。

        Returns:
            WalletResponse: 店舗ウォレットレスポンスです。
        """
        try:
            store_service = StoreService()
            return store_service.get_store_wallet(
                session=session,
                store_id=store_id
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @transaction
    def create_wallet_nonce(
        self,
        session: Session,
        store_id: int,
        request: WalletNonceCreateRequest,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名用の nonce を発行する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            request: nonce 発行に必要なウォレット情報。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        try:
            store_service = StoreService()
            return store_service.create_wallet_nonce(
                session=session,
                store_id=store_id,
                wallet_address=request.wallet_address,
                chain_type=request.chain_type,
                network_name=request.network_name,
            )
        except StoreNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=STORE_NOT_FOUND_ERROR
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
    
    @transaction
    def verify_and_create_wallet_nonce(
        self,
        session: Session,
        store_id: int,
        request: WalletVerifyRequest) -> WalletVerifyResponse:
        """署名済み nonce を検証し、店舗ウォレットを作成する。
        Args:
            session: SQLAlchemy のセッション。
            request: 店舗 ID、ウォレットアドレス、署名、チェーン種別、ネットワーク名を含む検証リクエスト。
        Returns:
            検証済みとして登録された店舗ウォレット情報。
        """
        try:
            store_service = StoreService()
            nonce_entity = store_service.verify_wallet_nonce(
                session=session,
                store_id=store_id,
                wallet_address=request.wallet_address,
                signature=request.signature,
                chain_type=request.chain_type,
                network_name=request.network_name
            )
            return store_service.create_store_wallet(
                session=session,
                store_id=store_id,
                wallet_address=request.wallet_address,
                chain_type=request.chain_type,
                network_name=request.network_name,
                chain_id=request.chain_id,
                nonce_entity=nonce_entity
            )
        except StoreNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=STORE_NOT_FOUND_ERROR
            )

        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=VERIFY_ERROR
            )
        
        except WalletConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=409,
                message=WALLET_CONFLICT_ERROR
            )
        
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @transaction
    def delete_wallet(self, session: Session, wallet_id: int) -> None:
        """登録済みウォレットの削除を行う。
        Args:
            session: SQLAlchemy のセッション。
            wallet_id: ウォレットID。
        Returns:
            なし。
        """
        try:
            StoreService().delete_wallet(
                session=session,
                wallet_id=wallet_id
            )

        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
