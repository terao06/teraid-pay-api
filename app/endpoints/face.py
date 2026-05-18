from fastapi import APIRouter
from app.controllers.face_controller import faceController
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.face_register_request import FaceRegisterRequest
from app.models.requests.face_delete_request import FaceDeleteRequest

face_router = APIRouter()


@face_router.post("/")
@response_rapper()
@request_rapper()
def register_face(request: FaceRegisterRequest):
    """ユーザーに顔画像を登録する

    Args:
        request: 顔画像登録リクエスト

    Returns:
        None
    """
    return faceController().register_face(request=request)


@face_router.delete("/")
@response_rapper()
@request_rapper()
def delete_face(request: FaceDeleteRequest):
    """ユーザーに顔画像を削除する

    Args:
        request: 顔画像削除リクエスト

    Returns:
        None
    """
    return faceController().delete_face(request=request)
