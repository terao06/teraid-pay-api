"""端末から利用する初回有効化エンドポイントを提供する。"""

from fastapi import APIRouter, Response

from app.controllers.device_controller import DeviceController
from app.middlewares.request_wrapper import request_device_rapper
from app.middlewares.response_wrapper import response_device_rapper
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.responses.device_activate_response import DeviceActivateResponse


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
