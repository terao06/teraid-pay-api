"""端末の顔認証決済サービスをHTTPエラー処理と接続する。"""

import logging

from app.core.exceptions.custom_exception import (
    CustomHttpException,
    DeviceCheckoutConflictException,
    DeviceCheckoutNotFoundException,
    FaceEmbeddingNotFoundException,
    FaceNotFoundException,
    InsufficientFundsError,
    SameFaceFoundException,
    UnauthorizedException,
    UserNotFoundException,
    WalletMismatchException,
    WalletNotFoundException,
    WalletNotPermittedException,
)
from app.core.exceptions.message import (
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    DEVICE_CHECKOUT_NOT_FOUND_ERROR,
    FACE_NOT_REGISTERED_ERROR,
    FACE_NOTE_FOUND_ERROR,
    INSUFFICIENT_FUNDS_ERROR,
    NOT_MATCH_ERROR,
    SAME_FACE_FOUND_ERROR,
    SERVER_ERROR,
    USER_NOT_FOUND_ERROR,
    WALLET_NOT_FOUND_ERROR,
    WALLET_NOT_PERMITTED_ERROR,
)
from app.models.requests.device_face_payment_request import DeviceFacePaymentRequest
from app.models.responses.device_face_payment_response import DeviceFacePaymentResponse
from app.services.device_payment_service import DevicePaymentService

logger = logging.getLogger(__name__)

_PAYMENT_ERRORS = {
    DeviceCheckoutNotFoundException: (404, DEVICE_CHECKOUT_NOT_FOUND_ERROR),
    FaceEmbeddingNotFoundException: (404, FACE_NOT_REGISTERED_ERROR),
    FaceNotFoundException: (400, FACE_NOTE_FOUND_ERROR),
    SameFaceFoundException: (400, SAME_FACE_FOUND_ERROR),
    UserNotFoundException: (404, USER_NOT_FOUND_ERROR),
    WalletNotFoundException: (404, WALLET_NOT_FOUND_ERROR),
    WalletNotPermittedException: (400, WALLET_NOT_PERMITTED_ERROR),
    WalletMismatchException: (400, NOT_MATCH_ERROR),
    InsufficientFundsError: (400, INSUFFICIENT_FUNDS_ERROR),
}


class DevicePaymentController:
    """端末決済の結果と業務エラーをHTTP応答へ変換する。

    Args:
        なし。

    Returns:
        端末決済用のコントローラー。
    """

    def start_face_payment(
        self, device_uuid: str, checkout_id: int, idempotency_key: str, request: DeviceFacePaymentRequest
    ) -> tuple[DeviceFacePaymentResponse, int]:
        """認証済みの端末の会計に対して顔認証決済を開始する。

        Args:
            device_uuid: 検証済みBearerトークンの端末UUID。
            checkout_id: 端末で確認した会計のID。
            idempotency_key: 同じ要求の再送を識別するキー。
            request: 検証済みの顔画像データ。

        Returns:
            決済試行のIDと状態を含む応答、およびHTTPステータス。

        Raises:
            HTTPException: 端末、会計、顔照合または決済の処理に失敗した場合。
        """
        try:
            return DevicePaymentService().start_face_payment(
                device_uuid=device_uuid,
                checkout_id=checkout_id,
                idempotency_key=idempotency_key,
                content=request.content,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except DeviceCheckoutConflictException as error:
            raise CustomHttpException.get_http_exception(status_code=409, message=str(error)) from None
        except tuple(_PAYMENT_ERRORS) as error:
            status, message = _PAYMENT_ERRORS[type(error)]
            raise CustomHttpException.get_http_exception(status_code=status, message=message) from None
        except Exception as error:
            logger.error("顔認証決済の開始に失敗しました (%s)", type(error).__name__)
            raise CustomHttpException.get_http_exception(status_code=500, message=SERVER_ERROR) from None
