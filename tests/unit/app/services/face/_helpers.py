from types import SimpleNamespace
from unittest.mock import Mock

from app.services.face_service import FaceService


def build_face_service(
    face_embedding_repository: Mock | None = None,
    user_repository: Mock | None = None,
    ssm_params: Mock | SimpleNamespace | None = None,
    s3_client: Mock | None = None,
) -> FaceService:
    """テスト用の FaceService インスタンスを構築する。"""
    service = FaceService.__new__(FaceService)
    service.face_embedding_repository = (
        face_embedding_repository if face_embedding_repository is not None else Mock()
    )
    service.user_repository = user_repository if user_repository is not None else Mock()
    service.ssm_params = ssm_params if ssm_params is not None else Mock()
    service.s3_client = s3_client if s3_client is not None else Mock()
    return service
