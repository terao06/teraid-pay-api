from fastapi import APIRouter
from app.controllers.face_controller import faceController
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.face_register_request import FaceImageProcessingRequest

payment_router = APIRouter()


@payment_router.post("/")
@response_rapper()
@request_rapper()
def register_face(request: FaceImageProcessingRequest):
    """ユーザーに顔画像を登録する

    Args:
        request: 顔画像登録リクエスト

    Returns:
        None
    """
    return faceController().register_face(request=request)
