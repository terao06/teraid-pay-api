"""端末用APIのBearer認証情報の取得とJWT検証を提供する。"""

import logging

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config.device_auth import get_device_auth_config
from app.core.exceptions.custom_exception import CustomHttpException, UnauthorizedException
from app.core.exceptions.message import DEVICE_AUTHENTICATION_FAILED_ERROR, SERVER_ERROR
from app.core.utils.device_auth import DeviceAuthUtil


logger = logging.getLogger(__name__)
device_bearer_scheme = HTTPBearer(auto_error=False, scheme_name="DeviceBearerAuth", bearerFormat="JWT")


def get_device_token_uuid(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Bearerトークンを検証し、DB接続前に端末UUIDを取得する。

    Args:
        credentials: Authorizationヘッダーから取得したBearer認証情報。

    Returns:
        検証済みトークンに含まれる端末UUID。

    Raises:
        HTTPException: トークンの欠落や不正は401、認証設定の読み込み失敗は500。
    """
    try:
        if credentials is None:
            raise UnauthorizedException()
        return DeviceAuthUtil.verify_access_token(credentials.credentials, get_device_auth_config())
    except UnauthorizedException:
        raise CustomHttpException.get_http_exception(
            status_code=401,
            message=DEVICE_AUTHENTICATION_FAILED_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except Exception as error:
        logger.error("端末アクセストークンの検証に失敗しました (%s)", type(error).__name__)
        raise CustomHttpException.get_http_exception(
            status_code=500,
            message=SERVER_ERROR,
        ) from None
