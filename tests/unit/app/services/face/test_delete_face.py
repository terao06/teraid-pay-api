from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    FaceEmbeddingNotFoundException,
    UserNotFoundException,
)
from app.models.postgres.face_embedding import ExtensionType
from app.services.face_service import FaceService


from ._helpers import build_face_service


class TestDeleteFace:
    """delete_face の動作を検証する。"""

    @patch("app.services.face_service.UserRepository")
    @patch("app.services.face_service.FaceEmbeddingRepository")
    @patch("app.services.face_service.S3Client")
    @patch("app.services.face_service.SsmClient")
    def test_delete_face_deletes_existing_face_embedding(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_repository_class,
        mock_user_repository_class,
    ) -> None:
        """正常系の処理結果を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        user = Mock()
        target_embedding = Mock()
        target_embedding.extension_type = ExtensionType.PNG
        ssm_params = SimpleNamespace(
            s3_endpoint="http://s3.local",
            face_image_bucket="faces",
        )
        mock_ssm_client_class.return_value = ssm_params
        mock_s3_client = mock_s3_client_class.return_value
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user
        mock_repository = mock_repository_class.return_value
        mock_repository.get_face_embedding_by_id.return_value = target_embedding
        service = FaceService()

        result = service.delete_face(
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result is None
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_repository_class.assert_called_once_with()
        mock_repository.get_face_embedding_by_id.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        mock_repository.delete_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            face_embedding=target_embedding,
        )
        assert mock_ssm_client_class.call_count == 2
        assert mock_s3_client_class.call_count == 2
        mock_s3_client_class.assert_called_with(s3_endpoint="http://s3.local")
        mock_s3_client.delete_object.assert_called_once_with(
            bucket_name="faces",
            file_name="101.png",
        )

    @patch("app.services.face_service.UserRepository")
    def test_delete_face_raises_user_not_found_when_user_does_not_exist(
        self,
        mock_user_repository_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 999
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = None
        service = build_face_service(user_repository=mock_user_repository)

        with pytest.raises(UserNotFoundException, match="ユーザーが存在しません。"):
            service.delete_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
            )

        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    @patch("app.services.face_service.UserRepository")
    @patch("app.services.face_service.FaceEmbeddingRepository")
    def test_delete_face_raises_face_embedding_not_found_when_face_is_not_registered(
        self,
        mock_repository_class,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        user = Mock()
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user
        mock_repository = mock_repository_class.return_value
        mock_repository.get_face_embedding_by_id.return_value = None
        service = build_face_service(
            face_embedding_repository=mock_repository,
            user_repository=mock_user_repository,
        )

        with pytest.raises(FaceEmbeddingNotFoundException, match="顔画像が登録されていません。"):
            service.delete_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
            )

        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_repository.get_face_embedding_by_id.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "対象のユーザーIDに顔画像は登録されていません。 user_id: 101"
        )
        mock_repository.delete_face_embedding.assert_not_called()
