import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image
import pytest

from app.core.exceptions.custom_exception import FaceConflictException, UserNotFoundException
from app.models.requests.face_register_request import ExtensionType
from app.services.face_service import FaceService


class TestRegisterFace:
    @patch("app.services.face_service.FaceEmbeddingRepository")
    @patch("app.services.face_service.FaceHelper.get_embedding")
    @patch("app.services.face_service.FaceHelper.alignment_face")
    @patch("app.services.face_service.FaceHelper.get_face_landmark")
    @patch("app.services.face_service.S3Client")
    @patch("app.services.face_service.SsmClient")
    def test_register_face_creates_embedding_and_uploads_original_image(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_face_landmark,
        mock_alignment_face,
        mock_get_embedding,
        mock_repository_class,
    ) -> None:
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        content = self._build_base64_image(format="PNG")
        ssm_params = SimpleNamespace(
            s3_endpoint="http://s3.local",
            llm_weight_bucket="weights",
            scrfd_weight="scrfd/model.onnx",
            adaface_weight="adaface/model.ckpt",
            face_image_bucket="faces",
        )
        s3_client = Mock()
        face_image = Mock()
        alignment_face = Image.new("RGB", (112, 112), color=(10, 20, 30))
        embedding = [0.1] * 512

        mock_ssm_client_class.return_value = ssm_params
        mock_s3_client_class.return_value = s3_client
        s3_client.get_object.side_effect = [b"scrfd-weight", b"adaface-weight"]
        uploaded_body = BytesIO()

        def capture_uploaded_file(bucket_name, file, filename) -> None:
            uploaded_body.write(file.read())

        s3_client.upload_object.side_effect = capture_uploaded_file
        mock_get_face_landmark.return_value = face_image
        mock_alignment_face.return_value = alignment_face
        mock_get_embedding.return_value = embedding
        mock_repository = mock_repository_class.return_value
        mock_repository.get_nearest_face_embedding.return_value = None

        service = FaceService()
        service.is_register_user = Mock(return_value=True)

        result = service.register_face(
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
            content=content,
            extension_type=ExtensionType.PNG,
        )

        assert result is None
        service.is_register_user.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_ssm_client_class.assert_called_once_with()
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        assert s3_client.get_object.call_args_list[0].kwargs == {
            "bucket_name": "weights",
            "key": "scrfd/model.onnx",
        }
        assert s3_client.get_object.call_args_list[1].kwargs == {
            "bucket_name": "weights",
            "key": "adaface/model.ckpt",
        }

        mock_get_face_landmark.assert_called_once()
        face_landmark_kwargs = mock_get_face_landmark.call_args.kwargs
        assert face_landmark_kwargs["weight_bytes"] == b"scrfd-weight"
        assert face_landmark_kwargs["image"].mode == "RGB"
        assert face_landmark_kwargs["image"].size == (160, 120)

        mock_alignment_face.assert_called_once_with(face_image=face_image)
        mock_get_embedding.assert_called_once_with(
            weight_bytes=b"adaface-weight",
            face_image=alignment_face,
        )

        mock_repository_class.assert_called_once_with()
        mock_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=0.7,
            exclusion_user_id=user_id,
        )
        mock_repository.create_face_embedding.assert_called_once()
        repository_kwargs = mock_repository.create_face_embedding.call_args.kwargs
        assert repository_kwargs["postgres_session"] is postgres_session
        created_embedding = repository_kwargs["face_embedding"]
        assert created_embedding.user_id == user_id
        assert created_embedding.embedding == embedding
        assert created_embedding.is_active is True

        s3_client.upload_object.assert_called_once()
        upload_kwargs = s3_client.upload_object.call_args.kwargs
        assert upload_kwargs["bucket_name"] == "faces"
        assert upload_kwargs["filename"] == "101.png"
        uploaded_body.seek(0)
        uploaded_image = Image.open(uploaded_body)
        assert uploaded_image.format == "PNG"
        assert uploaded_image.mode == "RGB"
        assert uploaded_image.size == (160, 120)

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    @patch("app.services.face_service.FaceEmbeddingRepository")
    @patch("app.services.face_service.FaceHelper.get_embedding")
    @patch("app.services.face_service.FaceHelper.alignment_face")
    @patch("app.services.face_service.FaceHelper.get_face_landmark")
    @patch("app.services.face_service.S3Client")
    @patch("app.services.face_service.SsmClient")
    def test_register_face_logs_distance_when_same_face_exists(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_face_landmark,
        mock_alignment_face,
        mock_get_embedding,
        mock_repository_class,
        mock_warning,
    ) -> None:
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        content = self._build_base64_image(format="PNG")
        ssm_params = SimpleNamespace(
            s3_endpoint="http://s3.local",
            llm_weight_bucket="weights",
            scrfd_weight="scrfd/model.onnx",
            adaface_weight="adaface/model.ckpt",
            face_image_bucket="faces",
        )
        s3_client = Mock()
        face_image = Mock()
        alignment_face = Image.new("RGB", (112, 112), color=(10, 20, 30))
        embedding = [0.1] * 512
        nearest_face = SimpleNamespace(
            face_embedding=SimpleNamespace(user_id=202),
            distance=0.1234,
        )

        mock_ssm_client_class.return_value = ssm_params
        mock_s3_client_class.return_value = s3_client
        s3_client.get_object.side_effect = [b"scrfd-weight", b"adaface-weight"]
        mock_get_face_landmark.return_value = face_image
        mock_alignment_face.return_value = alignment_face
        mock_get_embedding.return_value = embedding
        mock_repository = mock_repository_class.return_value
        mock_repository.get_nearest_face_embedding.return_value = nearest_face

        service = FaceService()
        service.is_register_user = Mock(return_value=True)

        with pytest.raises(FaceConflictException, match="この顔画像は既に登録されています。"):
            service.register_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
                content=content,
                extension_type=ExtensionType.PNG,
            )

        mock_warning.assert_called_once_with(
            "この顔画像は既に登録されています。 user_id: 202, distance: 0.1234"
        )
        mock_repository.create_face_embedding.assert_not_called()
        s3_client.upload_object.assert_not_called()

    def test_register_face_raises_user_not_found_when_user_does_not_exist(self) -> None:
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 999
        service = FaceService()
        service.is_register_user = Mock(return_value=False)

        with pytest.raises(UserNotFoundException, match="ユーザーが存在しません。"):
            service.register_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
                content=self._build_base64_image(format="PNG"),
                extension_type=ExtensionType.PNG,
            )

        service.is_register_user.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )

    @staticmethod
    def _build_base64_image(format: str) -> str:
        image = Image.new("RGB", (160, 120), color=(255, 0, 0))
        with BytesIO() as buffer:
            image.save(buffer, format=format)
            return base64.b64encode(buffer.getvalue()).decode("ascii")


class TestIsRegisterUser:
    @patch("app.services.face_service.UserRepository")
    def test_is_register_user_returns_true_when_user_exists(
        self,
        mock_repository_class,
    ) -> None:
        mysql_session = Mock()
        user_id = 101
        user = Mock()
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_by_id.return_value = user

        result = FaceService().is_register_user(
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result is True
        mock_repository_class.assert_called_once_with()
        mock_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )

    @patch("app.services.face_service.UserRepository")
    def test_is_register_user_returns_false_when_user_does_not_exist(
        self,
        mock_repository_class,
    ) -> None:
        mysql_session = Mock()
        user_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_user_by_id.return_value = None

        result = FaceService().is_register_user(
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result is False
        mock_repository_class.assert_called_once_with()
        mock_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
