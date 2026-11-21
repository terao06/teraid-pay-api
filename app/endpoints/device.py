"""端末の初回有効化、認証、来店セッション開始のエンドポイントを提供する。"""

from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPAuthorizationCredentials

from app.controllers.device_controller import DeviceController
from app.dependencies.device_auth import device_bearer_scheme, get_device_token_uuid
from app.middlewares.request_wrapper import request_device_rapper
from app.middlewares.response_wrapper import response_device_rapper
from app.models.requests.device_access_token_request import DeviceAccessTokenRequest
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.requests.visit_session_start_request import VisitSessionStartRequest
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse
from app.models.responses.device_activate_response import DeviceActivateResponse
from app.models.responses.visit_session_start_response import VisitSessionStartResponse


device_router = APIRouter()


@device_router.post("/activate")
@response_device_rapper()
@request_device_rapper()
def activate_device(
    response: Response,
    request: DeviceActivateRequest,
) -> DeviceActivateResponse:
    """端末を初回有効化し、一度限りの端末認証情報を返す。

    Args:
        response: レスポンスデコレーターがキャッシュ制御を設定するレスポンス。
        request: 有効化コードを含むリクエスト。

    Returns:
        端末UUIDと端末認証情報。

    Raises:
        HTTPException: 有効化コードが無効、または有効化処理に失敗した場合。
    """
    return DeviceController().activate_device(request=request)


@device_router.post("/auth/token")
@response_device_rapper()
@request_device_rapper()
def issue_device_access_token(
    response: Response,
    request: DeviceAccessTokenRequest,
) -> DeviceAccessTokenResponse:
    """端末認証情報を照合し、アクセストークンを返す。

    Args:
        response: レスポンスデコレーターがキャッシュ制御を設定するレスポンス。
        request: 端末UUIDと認証情報を含むリクエスト。

    Returns:
        端末アクセストークン、トークン種別、有効期間。

    Raises:
        HTTPException: 端末認証に失敗した場合、または発行処理に失敗した場合。
    """
    return DeviceController().issue_device_access_token(request=request)


@device_router.post("/visit-sessions", status_code=201)
@response_device_rapper()
@request_device_rapper()
def start_visit_session(
    response: Response,
    request: VisitSessionStartRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> VisitSessionStartResponse:
    """認証済み端末の来店セッションを開始する。

    Args:
        response: HTTPステータスとキャッシュ制御を設定するレスポンス。
        request: 開始要求IDを含むリクエスト。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        新規または既存の来店セッションID。

    Raises:
        HTTPException: 端末認証の失敗、開始要求の競合、またはセッション開始の失敗。
    """
    device_uuid = get_device_token_uuid(credentials)
    result, created = DeviceController().start_visit_session(device_uuid=device_uuid, request=request)
    if not created:
        response.status_code = 200
    return result
