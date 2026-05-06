from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import CustomHttpException, PaymentRequestNotFoundException, WalletNotApprovedException, WalletNotFoundException
from app.core.exceptions.message import NOT_MATCH_ERROR, PAYMENT_ERROR, PAYMENT_INFO_NOT_FOUND, SERVER_ERROR, WALLET_NOT_APPROVED_ERROR, WALLET_NOT_FOUND_ERROR
from app.middlewares.transaction import transaction
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.models.responses.payment_verify_response import PaymentVerifyResponse
from app.services.payment_service import PaymentService
from app.models.requests.payment_create_request import PaymentCreateRequest
from app.models.responses.payment_create_response import PaymentCreateResponse


class PaymentController:
    @transaction
    def create_payment_request(
        self,
        session: Session,
        request: PaymentCreateRequest) -> PaymentCreateResponse:
        """決済情報を作成する。

        Args:
            session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            request: nonce 発行に必要なウォレット情報。

        Returns:
            署名メッセージと nonce を含むレスポンス。
        """
        try:
            return PaymentService().create_payment_request(
                session=session,
                store_id=request.store_id,
                user_id=request.user_id,
                amount=request.amount
            )

        except WalletNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=WALLET_NOT_FOUND_ERROR
            )
        except ValueError:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=NOT_MATCH_ERROR
            )
        except WalletNotApprovedException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=WALLET_NOT_APPROVED_ERROR
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @transaction
    def execute_payment(
        self,
        session: Session,
        payment_request_id: int) -> PaymentTransactionHashResponse:
        try:
            return PaymentService().execute_payment(
                session=session,
                payment_request_id=payment_request_id,
            )

        except PaymentRequestNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=PAYMENT_INFO_NOT_FOUND
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
        
    @transaction
    def verify_transaction_hash(
        self,
        session: Session,
        payment_request_id: int) -> PaymentVerifyResponse:
        try:
            return PaymentService().verify_transaction_hash(
                session=session,
                payment_request_id=payment_request_id,
            )

        except PaymentRequestNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=PAYMENT_ERROR
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
