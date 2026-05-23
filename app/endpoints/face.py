from fastapi import APIRouter
from app.controllers.face_controller import faceController
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.face_register_request import FaceRegisterRequest
from app.models.requests.face_delete_request import FaceDeleteRequest
from app.models.requests.face_update_request import FaceUpdateRequest

face_router = APIRouter()

@face_router.get("/{user_id}")
@response_rapper()
@request_rapper()
def get_face_register_state(user_id: int):
    """ユーザーが顔登録済みか確認する

    Args:
        user_id: ユーザーID

    Returns:
        FaceRegisterStatusResponse: 顔登録登録状況ステータス
    """
    return faceController().get_face_register_state(user_id=user_id)


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


@face_router.put("/")
@response_rapper()
@request_rapper()
def update_face(request: FaceUpdateRequest):
    """ユーザーに顔画像を更新する

    Args:
        request: 顔画像更新リクエスト

    Returns:
        None
    """
    return faceController().update_face(request=request)


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
