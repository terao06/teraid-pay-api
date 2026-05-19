import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image
import pytest

from app.core.exceptions.custom_exception import (
    FaceConflictException,
    FaceEmbeddingAlreadyRegisterException,
    FaceEmbeddingNotFoundException,
    UserNotFoundException,
)
from app.models.postgres.face_embedding import ExtensionType
from app.services.face_service import FaceService


def _build_face_service(
    face_embedding_repository: Mock | None = None,
    user_repository: Mock | None = None,
    ssm_params: Mock | SimpleNamespace | None = None,
    s3_client: Mock | None = None,
) -> FaceService:
    service = FaceService.__new__(FaceService)
    service.face_embedding_repository = (
        face_embedding_repository if face_embedding_repository is not None else Mock()
    )
    service.user_repository = user_repository if user_repository is not None else Mock()
    service.ssm_params = ssm_params if ssm_params is not None else Mock()
    service.s3_client = s3_client if s3_client is not None else Mock()
    return service


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

        def capture_uploaded_file(bucket_name, file, file_name) -> None:
            uploaded_body.write(file.read())

        s3_client.upload_object.side_effect = capture_uploaded_file
        mock_get_face_landmark.return_value = face_image
        mock_alignment_face.return_value = alignment_face
        mock_get_embedding.return_value = embedding
        mock_repository = mock_repository_class.return_value
        mock_repository.get_nearest_face_embedding.return_value = None

        service = FaceService()
        service._validate_user_exists = Mock()
        service._validate_face_not_registered = Mock()

        result = service.register_face(
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
        service._validate_face_not_registered.assert_called_once_with(
            postgres_session=postgres_session,
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
        assert upload_kwargs["file_name"] == "101.png"
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
        service._validate_user_exists = Mock()
        service._validate_face_not_registered = Mock()

        with pytest.raises(FaceConflictException, match="この顔画像は既に登録されています。"):
            service.register_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
                content=content,
                extension_type=ExtensionType.PNG,
            )

        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service._validate_face_not_registered.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
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
        service = _build_face_service()
        service._validate_user_exists = Mock(
            side_effect=UserNotFoundException("ユーザーが存在しません。")
        )
        service._validate_face_not_registered = Mock()

        with pytest.raises(UserNotFoundException, match="ユーザーが存在しません。"):
            service.register_face(
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
        service._validate_face_not_registered.assert_not_called()

    @patch("app.services.face_service.S3Client")
    @patch("app.services.face_service.SsmClient")
    @patch("app.services.face_service.FaceEmbeddingRepository")
    def test_register_face_stops_when_face_is_already_registered(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        s3_client = Mock()
        service = _build_face_service(s3_client=s3_client)
        service._validate_user_exists = Mock()
        service._validate_face_not_registered = Mock(
            side_effect=FaceEmbeddingAlreadyRegisterException("すでに顔画像が登録されています。")
        )

        with pytest.raises(FaceEmbeddingAlreadyRegisterException, match="すでに顔画像が登録されています。"):
            service.register_face(
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
        service._validate_face_not_registered.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        s3_client.get_object.assert_not_called()
        s3_client.upload_object.assert_not_called()

    @staticmethod
    def _build_base64_image(format: str) -> str:
        image = Image.new("RGB", (160, 120), color=(255, 0, 0))
        with BytesIO() as buffer:
            image.save(buffer, format=format)
            return base64.b64encode(buffer.getvalue()).decode("ascii")


class TestDeleteFace:
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
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 999
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = None
        service = _build_face_service(user_repository=mock_user_repository)

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
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        user = Mock()
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user
        mock_repository = mock_repository_class.return_value
        mock_repository.get_face_embedding_by_id.return_value = None
        service = _build_face_service(
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


class TestFaceValidation:
    @patch("app.services.face_service.UserRepository")
    def test_validate_user_exists_returns_user_when_user_exists(
        self,
        mock_user_repository_class,
    ) -> None:
        mysql_session = Mock()
        user_id = 101
        user = Mock()
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user

        service = _build_face_service(user_repository=mock_user_repository)

        result = service._validate_user_exists(
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result is user
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    @patch("app.services.face_service.UserRepository")
    def test_validate_user_exists_raises_user_not_found_when_user_does_not_exist(
        self,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        mysql_session = Mock()
        user_id = 999
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = None

        with pytest.raises(UserNotFoundException, match="ユーザーが存在しません。"):
            service = _build_face_service(user_repository=mock_user_repository)
            service._validate_user_exists(
                mysql_session=mysql_session,
                user_id=user_id,
            )

        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "対象のユーザーは存在しません。 user_id: 999"
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    def test_validate_face_not_registered_raises_already_registered_when_face_exists(
        self,
        mock_warning,
    ) -> None:
        postgres_session = Mock()
        user_id = 101
        registered_face = Mock()
        service = _build_face_service()
        service.face_embedding_repository.get_face_embedding_by_id.return_value = registered_face

        with pytest.raises(FaceEmbeddingAlreadyRegisterException, match="すでに顔画像が登録されています。"):
            service._validate_face_not_registered(
                postgres_session=postgres_session,
                user_id=user_id,
            )

        service.face_embedding_repository.get_face_embedding_by_id.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "すでに顔画像が登録されています。 user_id: 101"
        )


class TestValidateFaceEmbedding:
    def test_validate_face_embedding_returns_none_when_same_face_does_not_exist(self) -> None:
        postgres_session = Mock()
        user_id = 101
        threshold = 0.7
        embedding = [0.1] * 512
        service = _build_face_service()
        service.face_embedding_repository.get_nearest_face_embedding.return_value = None

        result = service._validate_face_embedding(
            postgres_session=postgres_session,
            threshold=threshold,
            user_id=user_id,
            embedding=embedding,
        )

        assert result is None
        service.face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=threshold,
            exclusion_user_id=user_id,
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    def test_validate_face_embedding_raises_conflict_when_same_face_exists(
        self,
        mock_warning,
    ) -> None:
        postgres_session = Mock()
        user_id = 101
        threshold = 0.7
        embedding = [0.1] * 512
        nearest_face = SimpleNamespace(
            face_embedding=SimpleNamespace(user_id=202),
            distance=0.1234,
        )
        service = _build_face_service()
        service.face_embedding_repository.get_nearest_face_embedding.return_value = nearest_face

        with pytest.raises(FaceConflictException, match="この顔画像は既に登録されています。"):
            service._validate_face_embedding(
                postgres_session=postgres_session,
                threshold=threshold,
                user_id=user_id,
                embedding=embedding,
            )

        service.face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=threshold,
            exclusion_user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "この顔画像は既に登録されています。 user_id: 202, distance: 0.1234"
        )


class TestGetEmbeddingFromImage:
    @patch("app.services.face_service.FaceHelper.get_embedding")
    @patch("app.services.face_service.FaceHelper.alignment_face")
    @patch("app.services.face_service.FaceHelper.get_face_landmark")
    def test_get_embedding_from_image_returns_embedding(
        self,
        mock_get_face_landmark,
        mock_alignment_face,
        mock_get_embedding,
    ) -> None:
        image = Image.new("RGB", (160, 120), color=(255, 0, 0))
        face_image = Mock()
        alignment_face = Mock()
        embedding = [0.1] * 512
        ssm_params = SimpleNamespace(
            llm_weight_bucket="weights",
            scrfd_weight="scrfd/model.onnx",
            adaface_weight="adaface/model.ckpt",
        )
        s3_client = Mock()
        s3_client.get_object.side_effect = [b"scrfd-weight", b"adaface-weight"]
        mock_get_face_landmark.return_value = face_image
        mock_alignment_face.return_value = alignment_face
        mock_get_embedding.return_value = embedding
        service = _build_face_service(ssm_params=ssm_params, s3_client=s3_client)

        result = service._get_embedding_from_image(image=image)

        assert result == embedding
        assert s3_client.get_object.call_args_list[0].kwargs == {
            "bucket_name": "weights",
            "key": "scrfd/model.onnx",
        }
        assert s3_client.get_object.call_args_list[1].kwargs == {
            "bucket_name": "weights",
            "key": "adaface/model.ckpt",
        }
        mock_get_face_landmark.assert_called_once_with(
            weight_bytes=b"scrfd-weight",
            image=image,
        )
        mock_alignment_face.assert_called_once_with(face_image=face_image)
        mock_get_embedding.assert_called_once_with(
            weight_bytes=b"adaface-weight",
            face_image=alignment_face,
        )
