from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    CustomHttpException,
    PaymentRequestNotFoundException,
    WalletNotApprovedException,
    WalletNotFoundException
)
from app.core.exceptions.message import (
    NOT_MATCH_ERROR,
    PAYMENT_ERROR,
    PAYMENT_INFO_NOT_FOUND,
    SERVER_ERROR,
    WALLET_NOT_APPROVED_ERROR,
    WALLET_NOT_FOUND_ERROR
)
from app.middlewares.transaction import mysql_transaction
from app.models.requests.payment_create_request import PaymentCreateRequest
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.models.responses.payment_verify_response import PaymentVerifyResponse
from app.services.payment_service import PaymentService


class PaymentController:
    """決済 API のリクエストを処理するコントローラーです。"""

    @mysql_transaction
    def create_and_execute_payment(
        self,
        mysql_session: Session,
        request: PaymentCreateRequest
    ) -> PaymentTransactionHashResponse:
        """支払いリクエストを作成し、支払いを実行する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            request: 支払い作成に必要な店舗 ID、ユーザー ID、金額を含むリクエスト。

        Returns:
            支払い実行後のトランザクションハッシュ情報。
        """
        try:
            payment_service = PaymentService()
            payment_request = payment_service.create_payment_request(
                mysql_session=mysql_session,
                store_id=request.store_id,
                user_id=request.user_id,
                amount=request.amount,
            )
            return payment_service.execute_payment(
                mysql_session=mysql_session,
                payment_request_id=payment_request,
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
        except PaymentRequestNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=PAYMENT_INFO_NOT_FOUND
            )
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @mysql_transaction
    def verify_transaction_hash(
        self,
        mysql_session: Session,
        payment_request_id: int
    ) -> PaymentVerifyResponse:
        """支払いトランザクションハッシュを検証する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            payment_request_id: 検証対象の支払いリクエスト ID。

        Returns:
            支払い検証結果を含むレスポンス。
        """

        try:
            return PaymentService().verify_transaction_hash(
                mysql_session=mysql_session,
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
