import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image
import pytest

from app.core.exceptions.custom_exception import (
    FaceConflictException,
    FaceEmbeddingNotFoundException,
    UserNotFoundException,
)
from app.models.postgres.face_embedding import ExtensionType


from ._helpers import build_face_service


class TestUpdateFace:
    """update_face の動作を検証する。"""

    @patch("app.services.face_service.FaceHelper.get_embedding_from_image")
    def test_update_face_updates_embedding_and_uploads_original_image(
        self,
        mock_get_embedding_from_image,
    ) -> None:
        """正常系の処理結果を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        content = self._build_base64_image(format="PNG")
        registered_embedding = SimpleNamespace(
            user_id=user_id,
            embedding=[0.0] * 512,
            extension_type=ExtensionType.JPEG,
            is_active=True,
        )
        new_embedding = [0.2] * 512
        ssm_params = SimpleNamespace(face_image_bucket="faces")
        s3_client = Mock()
        uploaded_body = BytesIO()

        def capture_uploaded_file(bucket_name, file, file_name) -> None:
            uploaded_body.write(file.read())

        s3_client.upload_object.side_effect = capture_uploaded_file
        service = build_face_service(ssm_params=ssm_params, s3_client=s3_client)
        service._validate_user_exists = Mock()
        service._get_registered_face_embedding = Mock(return_value=registered_embedding)
        mock_get_embedding_from_image.return_value = new_embedding
        service._validate_face_embedding = Mock()

        result = service.update_face(
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
            content=content,
            extension_type=ExtensionType.PNG,
        )

        assert result is None
        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service._get_registered_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        mock_get_embedding_from_image.assert_called_once()
        embedding_kwargs = mock_get_embedding_from_image.call_args.kwargs
        assert embedding_kwargs["s3_client"] is s3_client
        assert embedding_kwargs["ssm_params"] is ssm_params
        target_image = embedding_kwargs["image"]
        assert target_image.mode == "RGB"
        assert target_image.size == (160, 120)
        service._validate_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            threshold=0.7,
            user_id=user_id,
            embedding=new_embedding,
        )
        assert registered_embedding.embedding == new_embedding
        assert registered_embedding.extension_type == ExtensionType.PNG
        service.face_embedding_repository.update_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            face_embedding=registered_embedding,
        )
        service.face_embedding_repository.create_face_embedding.assert_not_called()
        s3_client.upload_object.assert_called_once()
        upload_kwargs = s3_client.upload_object.call_args.kwargs
        assert upload_kwargs["bucket_name"] == "faces"
        assert upload_kwargs["file_name"] == "101.png"
        uploaded_body.seek(0)
        uploaded_image = Image.open(uploaded_body)
        assert uploaded_image.format == "PNG"
        assert uploaded_image.mode == "RGB"
        assert uploaded_image.size == (160, 120)

    @patch("app.services.face_service.FaceHelper.get_embedding_from_image")
    def test_update_face_raises_user_not_found_when_user_does_not_exist(
        self,
        mock_get_embedding_from_image,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 999
        s3_client = Mock()
        service = build_face_service(s3_client=s3_client)
        service._validate_user_exists = Mock(
            side_effect=UserNotFoundException("user not found")
        )
        service._get_registered_face_embedding = Mock()

        with pytest.raises(UserNotFoundException, match="user not found"):
            service.update_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
                content=self._build_base64_image(format="PNG"),
                extension_type=ExtensionType.PNG,
            )

        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service._get_registered_face_embedding.assert_not_called()
        mock_get_embedding_from_image.assert_not_called()
        s3_client.upload_object.assert_not_called()

    @patch("app.services.face_service.FaceHelper.get_embedding_from_image")
    def test_update_face_raises_not_found_when_face_is_not_registered(
        self,
        mock_get_embedding_from_image,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        s3_client = Mock()
        service = build_face_service(s3_client=s3_client)
        service._validate_user_exists = Mock()
        service._get_registered_face_embedding = Mock(
            side_effect=FaceEmbeddingNotFoundException("face embedding not found")
        )

        with pytest.raises(FaceEmbeddingNotFoundException, match="face embedding not found"):
            service.update_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
                content=self._build_base64_image(format="PNG"),
                extension_type=ExtensionType.PNG,
            )

        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service._get_registered_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        mock_get_embedding_from_image.assert_not_called()
        service.face_embedding_repository.update_face_embedding.assert_not_called()
        s3_client.upload_object.assert_not_called()

    @patch("app.services.face_service.FaceHelper.get_embedding_from_image")
    def test_update_face_stops_when_same_face_exists(
        self,
        mock_get_embedding_from_image,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        registered_embedding = SimpleNamespace(
            user_id=user_id,
            embedding=[0.0] * 512,
            extension_type=ExtensionType.JPEG,
            is_active=True,
        )
        new_embedding = [0.2] * 512
        s3_client = Mock()
        service = build_face_service(s3_client=s3_client)
        service._validate_user_exists = Mock()
        service._get_registered_face_embedding = Mock(return_value=registered_embedding)
        mock_get_embedding_from_image.return_value = new_embedding
        service._validate_face_embedding = Mock(
            side_effect=FaceConflictException("face conflict")
        )

        with pytest.raises(FaceConflictException, match="face conflict"):
            service.update_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
                content=self._build_base64_image(format="PNG"),
                extension_type=ExtensionType.PNG,
            )

        service._validate_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            threshold=0.7,
            user_id=user_id,
            embedding=new_embedding,
        )
        assert registered_embedding.embedding == [0.0] * 512
        assert registered_embedding.extension_type == ExtensionType.JPEG
        service.face_embedding_repository.update_face_embedding.assert_not_called()
        s3_client.upload_object.assert_not_called()

    @staticmethod
    def _build_base64_image(format: str) -> str:
        image = Image.new("RGB", (160, 120), color=(255, 0, 0))
        with BytesIO() as buffer:
            image.save(buffer, format=format)
            return base64.b64encode(buffer.getvalue()).decode("ascii")
