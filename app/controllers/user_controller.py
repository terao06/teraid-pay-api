from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    CustomHttpException,
    UnauthorizedException,
    UserNotFoundException,
    WalletConflictException,
    WalletNotApprovedException,
    WalletNotFoundException
)
from app.core.exceptions.message import (
    SERVER_ERROR,
    USER_NOT_FOUND_ERROR,
    VERIFY_ERROR,
    WALLET_CONFLICT_ERROR,
    WALLET_IS_ALREADY_EXIST,
    WALLET_NOT_APPROVED_ERROR,
    WALLET_NOT_FOUND_ERROR
)
from app.middlewares.transaction import mysql_transaction
from app.models.requests.wallet_nonce_create_request import WalletNonceCreateRequest
from app.models.requests.wallet_nonce_verify_request import WalletVerifyRequest
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.models.responses.wallet_approval_response import WalletApprovalResponse
from app.models.responses.wallet_response import WalletResponse
from app.services.user_service import UserService


class UserController:
    """ユーザーウォレット取得 API のリクエストを処理するコントローラーです。"""

    @mysql_transaction
    def get_user_wallet(self, mysql_session: Session, user_id: int) -> WalletResponse | None:
        """リクエスト条件に一致するユーザーウォレットを取得します。

        Args:
            mysql_session: SQLAlchemy のセッションです。
            user_id: 取得対象のユーザーIDです。

        Returns:
            WalletResponse: ユーザーウォレットレスポンスです。
        """
        try:
            store_service = UserService()
            return store_service.get_user_wallet(
                mysql_session=mysql_session,
                user_id=user_id
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def get_user_wallet_approval(self, mysql_session: Session, user_id: int) -> WalletApprovalResponse:
        try:
            approval = UserService().get_user_wallet_approval(
                mysql_session=mysql_session,
                user_id=user_id
            )
            if approval is None:
                raise CustomHttpException.get_http_exception(
                    status_code=404,
                    message=WALLET_NOT_FOUND_ERROR
                )
            return approval
        except HTTPException:
            raise
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def update_wallet_approval_state(self, mysql_session: Session, wallet_id: int, tx_hash: str) -> None:
        try:
            UserService().update_wallet_approval_state(
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                tx_hash=tx_hash,
            )
        except WalletNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=WALLET_NOT_FOUND_ERROR)

        except WalletNotApprovedException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=WALLET_NOT_APPROVED_ERROR)

        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def create_wallet_nonce(
        self,
        mysql_session: Session,
        user_id: int,
        request: WalletNonceCreateRequest,
    ) -> WalletNonceCreateResponse:
        """ウォレット署名用の nonce を発行する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: 対象ユーザーの ID。
            request: nonce 発行に必要なウォレット情報。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        try:
            store_service = UserService()
            return store_service.create_wallet_nonce(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=request.wallet_address,
                chain_type=request.chain_type,
                network_name=request.network_name,
            )

        except UserNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=USER_NOT_FOUND_ERROR
            )
        
        except WalletConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=WALLET_IS_ALREADY_EXIST
            )

        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def verify_and_create_wallet_nonce(
        self,
        mysql_session: Session,
        user_id: int,
        request: WalletVerifyRequest) -> WalletVerifyResponse:
        """署名済み nonce を検証し、店舗ウォレットを作成する。
        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: ユーザーID
            request: ウォレットアドレス、署名、チェーン種別、ネットワーク名を含む検証リクエスト。
        Returns:
            検証済みとして登録された店舗ウォレット情報。
        """
        try:
            user_service = UserService()
            nonce_entity = user_service.verify_wallet_nonce(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=request.wallet_address,
                signature=request.signature,
                chain_type=request.chain_type,
                network_name=request.network_name
            )
            return user_service.create_user_wallet(
                mysql_session=mysql_session,
                user_id=user_id,
                wallet_address=request.wallet_address,
                chain_type=request.chain_type,
                network_name=request.network_name,
                token_symbol=request.token_symbol,
                chain_id=request.chain_id,
                nonce_entity=nonce_entity
            )
        except UserNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=USER_NOT_FOUND_ERROR
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

    @mysql_transaction
    def delete_wallet(self, mysql_session: Session, wallet_id: int) -> None:
        """登録済みウォレットの削除を行う。
        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_id: ウォレットID。
        Returns:
            なし。
        """
        try:
            UserService().delete_wallet(
                mysql_session=mysql_session,
                wallet_id=wallet_id
            )

        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
