"""端末用APIのトランザクションとHTTPエラー変換を提供する。"""

import logging

from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    CustomHttpException,
    DeviceActivationCodeInvalidException,
    UnauthorizedException,
)
from app.core.exceptions.message import (
    DEVICE_ACTIVATION_CODE_INVALID_ERROR,
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    SERVER_ERROR,
)
from app.middlewares.transaction import mysql_transaction
from app.models.requests.device_access_token_request import DeviceAccessTokenRequest
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse
from app.models.responses.device_activate_response import DeviceActivateResponse
from app.services.device_service import DeviceService


logger = logging.getLogger(__name__)


class DeviceController:
    """端末用APIの業務処理を呼び出すコントローラー。

    Args:
        なし。

    Returns:
        端末用APIのコントローラー。
    """

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def activate_device(
        self,
        mysql_session: Session,
        request: DeviceActivateRequest,
    ) -> DeviceActivateResponse:
        """初回有効化をコミットし、失敗時はHTTP例外に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            request: 検証済みの有効化リクエスト。

        Returns:
            コミット済みの端末UUIDと端末認証情報。

        Raises:
            HTTPException: コードを利用できない場合は400、処理に失敗した場合は500。
        """
        try:
            return DeviceService().activate_device(
                mysql_session=mysql_session,
                activation_code=request.activation_code,
            )
        except DeviceActivationCodeInvalidException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=DEVICE_ACTIVATION_CODE_INVALID_ERROR,
            ) from None
        except Exception as error:
            logger.error("端末初回有効化処理に失敗しました (%s)", type(error).__name__)
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            ) from None

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def issue_device_access_token(
        self,
        mysql_session: Session,
        request: DeviceAccessTokenRequest,
    ) -> DeviceAccessTokenResponse:
        """最終認証日時の更新をコミットした後にアクセストークンを返す。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            request: 検証済みの端末認証リクエスト。

        Returns:
            端末アクセストークン、トークン種別、有効期間。

        Raises:
            HTTPException: 端末認証に失敗した場合は401、発行処理に失敗した場合は500。
        """
        try:
            return DeviceService().issue_device_access_token(
                mysql_session=mysql_session,
                device_uuid=str(request.device_uuid),
                device_credential=request.device_credential,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
            ) from None
        except Exception as error:
            logger.error("端末アクセストークン発行処理に失敗しました (%s)", type(error).__name__)
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            ) from None
